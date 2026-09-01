import { useEffect, useMemo, useState } from "react";
import { getPredictionsUpcoming, getGlobalTournaments, getGlobalPredictionsTournament, getGlobalPredictionsLive } from "../lib/api";
import { buildRollingDays, toISODate } from "../lib/dateUtils";
import MatchCard from "../components/MatchCard";
import { Zap, Globe, Radio } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";

// Sorted tournaments by expected relevance (in-season now first)
const PRIORITY_TIDS = [649, 40, 215, 410, 39, 41, 777, 782, 17, 8, 35, 23, 34, 242, 325, 955, 71, 152];

export default function Predictions() {
  const [tab, setTab] = useState("europe");
  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <div className="flex items-center gap-3 mb-2">
        <Zap className="w-6 h-6 text-purple-400" />
        <h1 className="text-3xl md:text-4xl font-black tracking-tight">AI Predictions</h1>
      </div>
      <p className="text-slate-400">Upcoming matches with 1X2, BTTS, Over/Under and correct-score picks.</p>

      <Tabs value={tab} onValueChange={setTab} className="mt-6">
        <TabsList className="bg-white/5">
          <TabsTrigger value="europe">Football-data</TabsTrigger>
          <TabsTrigger value="world"><Globe className="w-4 h-4 mr-1" /> Worldwide</TabsTrigger>
          <TabsTrigger value="live"><Radio className="w-4 h-4 mr-1" /> Live</TabsTrigger>
        </TabsList>
        <TabsContent value="europe" className="mt-6"><FootballDataPredictions /></TabsContent>
        <TabsContent value="world" className="mt-6"><WorldwidePredictions /></TabsContent>
        <TabsContent value="live" className="mt-6"><LivePredictions /></TabsContent>
      </Tabs>
    </div>
  );
}

function FootballDataPredictions() {
  const days = useMemo(() => buildRollingDays(7), []);
  const [selectedIdx, setSelectedIdx] = useState(0); // today
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const res = await getPredictionsUpcoming(7, 30);
        if (!alive) return;
        setMatches(res.matches || []);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const dayMatches = useMemo(() => {
    const selectedDate = toISODate(days[selectedIdx]);
    return matches.filter((m) => (m.utcDate || "").slice(0, 10) === selectedDate);
  }, [matches, days, selectedIdx]);

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap mb-4 overflow-x-auto no-scrollbar pb-1">
        {days.map((d, i) => {
          const label = i === 0 ? "Today" : i === 1 ? "Tomorrow" : d.toLocaleDateString([], { weekday: "short" });
          const sub = i > 1 ? ` ${d.getDate()}` : "";
          return (
            <button key={i} onClick={() => setSelectedIdx(i)}
              className={`px-3 py-1.5 rounded-md text-sm border transition whitespace-nowrap ${
                selectedIdx === i ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
              }`}>{label}{sub}</button>
          );
        })}
      </div>
      <p className="text-xs text-slate-500 mb-4">Premier League, La Liga, Bundesliga, Serie A, Ligue 1 resume Aug 6–Aug 21. Currently active: Brasileirão.</p>
      {loading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(9)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-40 animate-pulse" />))}
        </div>
      ) : dayMatches.length === 0 ? (
        <div className="nt-card rounded-xl p-8 text-center text-slate-400">No matches with predictions on this day.</div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dayMatches.map((m) => <MatchCard key={m.id} match={m} />)}
        </div>
      )}
    </>
  );
}

function WorldwidePredictions() {
  const [tournaments, setTournaments] = useState([]);
  const [selected, setSelected] = useState(649); // Chinese Super
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getGlobalTournaments().then((d) => {
      const t = (d.tournaments || []).sort((a, b) => PRIORITY_TIDS.indexOf(a.id) - PRIORITY_TIDS.indexOf(b.id));
      setTournaments(t);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true); setError(null);
      try {
        const d = await getGlobalPredictionsTournament(selected, 12);
        if (!alive) return;
        setMatches(d.matches || []);
        if (d.error) setError(d.error);
      } catch (e) {
        if (alive) setError(e?.response?.data?.detail || e.message);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [selected]);

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap mb-4">
        {tournaments.slice(0, 12).map((t) => (
          <button key={t.id} onClick={() => setSelected(t.id)}
            className={`px-3 py-1.5 rounded-md text-sm border transition ${
              selected === t.id ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
            }`}>{t.name}</button>
        ))}
      </div>
      <p className="text-xs text-slate-500 mb-4">Predictions computed from real team form via SportApi7 (last 10 matches per team). Cached to respect the free RapidAPI quota.</p>
      {error && <div className="nt-card rounded-xl p-4 mb-4 text-sm text-amber-300 border-amber-500/30">{error}</div>}
      {loading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-40 animate-pulse" />))}
        </div>
      ) : matches.length === 0 ? (
        <div className="nt-card rounded-xl p-8 text-center text-slate-400">No upcoming matches or predictions available for this league.</div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {matches.map((m) => <MatchCard key={m.id} match={m} />)}
        </div>
      )}
    </>
  );
}

function LivePredictions() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    getGlobalPredictionsLive(12)
      .then((d) => { if (alive) setMatches(d.matches || []); })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);
  return (
    <>
      <p className="text-xs text-slate-500 mb-4">Live matches worldwide with predictions from team form. Pre-match probabilities — outcome may already be shifting.</p>
      {loading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-40 animate-pulse" />))}
        </div>
      ) : matches.length === 0 ? (
        <div className="nt-card rounded-xl p-8 text-center text-slate-400">No live matches with predictions right now.</div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {matches.map((m) => <MatchCard key={m.id} match={m} />)}
        </div>
      )}
    </>
  );
}
