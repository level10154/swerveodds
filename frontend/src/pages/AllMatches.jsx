import { useEffect, useMemo, useState } from "react";
import { getMatchesRange, getWorldMatchesToday } from "../lib/api";
import MatchCard from "../components/MatchCard";
import { Button } from "../components/ui/button";
import { Globe } from "lucide-react";

function toISODate(d) { return d.toISOString().slice(0, 10); }

export default function AllMatches() {
  const dates = useMemo(() => {
    const today = new Date();
    return Array.from({ length: 9 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() + (i - 2));
      return d;
    });
  }, []);
  const [selectedIdx, setSelectedIdx] = useState(2); // today
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [includeWorld, setIncludeWorld] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      const d = toISODate(dates[selectedIdx]);
      const next = new Date(dates[selectedIdx]); next.setDate(next.getDate() + 1);
      try {
        const res = await getMatchesRange(d, toISODate(next), false);
        let list = res.matches || [];
        // Only augment "today" with worldwide feed (TheSportsDB day events)
        const isToday = selectedIdx === 2;
        if (isToday && includeWorld) {
          try {
            const wr = await getWorldMatchesToday();
            const existing = new Set(list.map((m) => `${(m.homeTeam?.name || "").toLowerCase()}-${(m.awayTeam?.name || "").toLowerCase()}`));
            for (const m of wr.matches || []) {
              const k = `${(m.homeTeam?.name || "").toLowerCase()}-${(m.awayTeam?.name || "").toLowerCase()}`;
              if (!existing.has(k)) list.push(m);
            }
          } catch {}
        }
        if (!alive) return;
        setMatches(list);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [selectedIdx, dates, includeWorld]);

  const groups = useMemo(() => {
    const g = {};
    for (const m of matches) {
      const k = m.competition?.name || "Other";
      (g[k] = g[k] || []).push(m);
    }
    return g;
  }, [matches]);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <h1 className="text-3xl md:text-4xl font-black tracking-tight">All Football Fixtures</h1>
      <p className="text-slate-400 mt-1">Live scores, upcoming matches & results from worldwide leagues.</p>

      <div className="mt-4 flex items-center gap-2 text-xs">
        <button
          onClick={() => setIncludeWorld(!includeWorld)}
          className={`px-3 py-1.5 rounded-md border inline-flex items-center gap-1.5 transition ${
            includeWorld ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200" : "bg-white/[0.03] border-white/5 text-slate-400"
          }`}
        >
          <Globe className="w-3.5 h-3.5" /> Include worldwide fixtures {includeWorld ? "ON" : "OFF"}
        </button>
      </div>

      <div className="mt-6 flex items-center gap-2 overflow-x-auto no-scrollbar pb-2">
        {dates.map((d, i) => {
          const isToday = i === 2;
          const active = i === selectedIdx;
          const label = isToday ? "Today" : d.toLocaleDateString([], { weekday: "short" });
          const sub = d.toLocaleDateString([], { month: "short", day: "numeric" });
          return (
            <button
              key={i}
              onClick={() => setSelectedIdx(i)}
              className={`min-w-[90px] rounded-lg px-3 py-2 text-sm border transition ${
                active ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              <div className="font-semibold">{label}</div>
              <div className="text-[11px] text-slate-400">{sub}</div>
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-32 animate-pulse" />))}
          </div>
        ) : matches.length === 0 ? (
          <div className="nt-card rounded-xl p-8 text-center text-slate-400">No matches on this date.</div>
        ) : (
          Object.entries(groups).map(([league, list]) => (
            <div key={league} className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                {list[0].competition?.emblem && <img src={list[0].competition.emblem} alt="" className="w-5 h-5" />}
                <h2 className="font-bold text-sm uppercase tracking-wide text-slate-300">{league}</h2>
                <span className="text-xs text-slate-500">({list.length})</span>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {list.map((m) => <MatchCard key={m.id} match={m} />)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
