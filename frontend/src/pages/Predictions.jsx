import { useEffect, useState } from "react";
import { getPredictionsUpcoming } from "../lib/api";
import MatchCard from "../components/MatchCard";
import { Zap } from "lucide-react";

export default function Predictions() {
  const [days, setDays] = useState(1);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const res = await getPredictionsUpcoming(days, 30);
        if (!alive) return;
        setMatches(res.matches || []);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [days]);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <div className="flex items-center gap-3 mb-2">
        <Zap className="w-6 h-6 text-purple-400" />
        <h1 className="text-3xl md:text-4xl font-black tracking-tight">AI Predictions</h1>
      </div>
      <p className="text-slate-400">Upcoming matches with 1X2, BTTS, Over/Under and correct-score picks.</p>

      <div className="mt-6 flex items-center gap-2">
        {[{v:1,l:"Today"},{v:2,l:"Next 2 days"},{v:3,l:"Next 3 days"},{v:7,l:"Next week"}].map((o) => (
          <button key={o.v} onClick={()=>setDays(o.v)}
            className={`px-3 py-1.5 rounded-md text-sm border transition ${
              days===o.v ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
            }`}>{o.l}</button>
        ))}
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(9)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-40 animate-pulse" />))}
          </div>
        ) : matches.length === 0 ? (
          <div className="nt-card rounded-xl p-8 text-center text-slate-400">No upcoming matches with predictions in this window.</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {matches.map((m) => <MatchCard key={m.id} match={m} />)}
          </div>
        )}
      </div>
    </div>
  );
}
