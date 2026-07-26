import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getGlobalLive } from "../lib/api";
import { Radio, Clock } from "lucide-react";

export default function LiveMatches() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [country, setCountry] = useState("all");

  useEffect(() => {
    let alive = true;
    let interval;
    const load = async () => {
      try {
        const d = await getGlobalLive(80);
        if (alive) setMatches(d.matches || []);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    interval = setInterval(load, 120000); // refresh every 2 min
    return () => { alive = false; if (interval) clearInterval(interval); };
  }, []);

  const countries = Array.from(new Set(matches.map((m) => m.area?.name).filter(Boolean))).sort();
  const filtered = country === "all" ? matches : matches.filter((m) => m.area?.name === country);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <div className="flex items-center gap-3 mb-2">
        <div className="relative">
          <Radio className="w-6 h-6 text-rose-400" />
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-rose-500 rounded-full animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-4xl font-black tracking-tight">Live Now</h1>
        <span className="text-xs bg-rose-500/15 border border-rose-500/30 text-rose-300 px-2 py-0.5 rounded-md font-semibold">{matches.length} matches</span>
      </div>
      <p className="text-slate-400">Real-time worldwide football — auto-refreshes every 2 minutes.</p>

      {countries.length > 0 && (
        <div className="mt-6 flex items-center gap-2 flex-wrap">
          <button onClick={() => setCountry("all")}
            className={`px-3 py-1.5 rounded-md text-sm border transition ${
              country === "all" ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
            }`}>All ({matches.length})</button>
          {countries.map((c) => {
            const n = matches.filter((m) => m.area?.name === c).length;
            return (
              <button key={c} onClick={() => setCountry(c)}
                className={`px-3 py-1.5 rounded-md text-sm border transition ${
                  country === c ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
                }`}>{c} ({n})</button>
            );
          })}
        </div>
      )}

      <div className="mt-6">
        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(9)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-24 animate-pulse" />))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="nt-card rounded-xl p-8 text-center text-slate-400">No live matches. Check back soon.</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((m) => <LiveCard key={m.id} match={m} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function LiveCard({ match }) {
  const s = match.score?.fullTime || {};
  const hs = s.home ?? 0;
  const as = s.away ?? 0;
  return (
    <div className="nt-card rounded-xl p-3 relative overflow-hidden">
      <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] font-bold text-rose-300">
        <span className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-pulse" /> LIVE
      </div>
      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-2">
        {match.competition?.emblem && <img src={match.competition.emblem} alt="" className="w-3.5 h-3.5" onError={(e)=>{e.currentTarget.style.display='none';}} />}
        <span className="truncate">{match.competition?.name}</span>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {match.homeTeam?.crest && <img src={match.homeTeam.crest} alt="" className="w-5 h-5 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />}
          <span className="text-sm font-semibold truncate">{match.homeTeam?.shortName || match.homeTeam?.name}</span>
        </div>
        <div className="text-center font-black text-lg">
          <span className={hs > as ? "text-emerald-400" : ""}>{hs}</span>
          <span className="text-slate-500 mx-1">-</span>
          <span className={as > hs ? "text-emerald-400" : ""}>{as}</span>
        </div>
        <div className="flex items-center gap-1.5 justify-end min-w-0">
          <span className="text-sm font-semibold truncate text-right">{match.awayTeam?.shortName || match.awayTeam?.name}</span>
          {match.awayTeam?.crest && <img src={match.awayTeam.crest} alt="" className="w-5 h-5 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />}
        </div>
      </div>
    </div>
  );
}
