import { Link } from "react-router-dom";
import { Sparkles, TrendingUp, Trophy } from "lucide-react";
import { Button } from "./ui/button";

export default function BetOfDayCard({ match, loading }) {
  if (loading || !match) {
    return (
      <div className="nt-card rounded-2xl p-6 min-h-[280px] flex items-center justify-center text-slate-400">
        {loading ? "Loading bet of the day..." : "No matches available today"}
      </div>
    );
  }
  const p = match.prediction;
  return (
    <div className="nt-card rounded-2xl p-6 relative overflow-hidden">
      <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full bg-purple-600/20 blur-3xl" />
      <div className="absolute -bottom-16 -left-16 w-56 h-56 rounded-full bg-fuchsia-600/15 blur-3xl" />
      <div className="relative">
        <div className="flex items-center gap-2 mb-4">
          <span className="nt-chip px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> BET OF THE DAY
          </span>
          <span className="text-xs text-slate-400">{match.competition?.name}</span>
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 mb-6">
          <div className="flex flex-col items-center text-center gap-2">
            {match.homeTeam?.crest && <img src={match.homeTeam.crest} alt="" className="w-14 h-14 object-contain" />}
            <span className="font-semibold text-sm">{match.homeTeam?.shortName || match.homeTeam?.name}</span>
          </div>
          <div className="text-center">
            <div className="text-3xl font-black text-white/80">VS</div>
            <div className="text-[11px] text-slate-400 mt-1">{new Date(match.utcDate).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</div>
          </div>
          <div className="flex flex-col items-center text-center gap-2">
            {match.awayTeam?.crest && <img src={match.awayTeam.crest} alt="" className="w-14 h-14 object-contain" />}
            <span className="font-semibold text-sm">{match.awayTeam?.shortName || match.awayTeam?.name}</span>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-3 mb-5">
          <div className="rounded-lg bg-white/5 p-3">
            <div className="text-[10px] uppercase text-slate-400">Recommended</div>
            <div className="font-bold text-white mt-0.5">{p?.best_bet?.market}</div>
            <div className="text-purple-300 text-sm">{p?.best_bet?.pick}</div>
          </div>
          <div className="rounded-lg bg-white/5 p-3">
            <div className="text-[10px] uppercase text-slate-400">Confidence</div>
            <div className="font-black text-2xl text-emerald-400 mt-0.5">{p?.best_bet?.confidence}%</div>
          </div>
          <div className="rounded-lg bg-white/5 p-3">
            <div className="text-[10px] uppercase text-slate-400">Likely Score</div>
            <div className="font-bold text-white mt-0.5">{p?.most_likely_score?.score}</div>
            <div className="text-slate-400 text-xs">{p?.most_likely_score?.prob}% probability</div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link to={`/match/${match.id}`} className="flex-1">
            <Button className="nt-btn-primary w-full">See Full Analysis</Button>
          </Link>
          <div className="text-xs text-slate-400 hidden md:flex items-center gap-1">
            <Trophy className="w-3.5 h-3.5" /> Powered by NerdyStats AI
          </div>
        </div>
      </div>
    </div>
  );
}
