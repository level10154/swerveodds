import { Link } from "react-router-dom";
import { Clock, TrendingUp, Zap } from "lucide-react";

function StatusBadge({ status, minute }) {
  const map = {
    IN_PLAY: { label: minute ? `${minute}'` : "LIVE", cls: "bg-rose-500/20 text-rose-300 border-rose-500/30" },
    PAUSED: { label: "HT", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
    FINISHED: { label: "FT", cls: "bg-slate-500/20 text-slate-300 border-slate-500/30" },
    TIMED: null,
    SCHEDULED: null,
  };
  const cfg = map[status];
  if (!cfg) return null;
  return <span className={`text-[10px] px-2 py-0.5 rounded-md border font-semibold ${cfg.cls}`}>{cfg.label}</span>;
}

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

export default function MatchCard({ match }) {
  const p = match.prediction;
  const isLive = match.status === "IN_PLAY" || match.status === "PAUSED";
  const isFinished = match.status === "FINISHED";
  const ft = match.score?.fullTime || {};
  return (
    <Link to={`/match/${match.id}`} className="nt-card rounded-xl p-4 block transition">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {match.competition?.emblem && (
            <img src={match.competition.emblem} alt="" className="w-5 h-5 object-contain" onError={(e)=>{e.currentTarget.style.display='none';}} />
          )}
          <span className="text-xs text-slate-400 truncate">{match.competition?.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={match.status} minute={match.minute} />
          <span className="text-xs text-slate-400 flex items-center gap-1"><Clock className="w-3 h-3" />{formatTime(match.utcDate)}</span>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {match.homeTeam?.crest && <img src={match.homeTeam.crest} alt="" className="w-7 h-7 object-contain" />}
          <span className="font-semibold text-sm truncate">{match.homeTeam?.shortName || match.homeTeam?.name}</span>
        </div>
        <div className="text-center">
          {isFinished || isLive ? (
            <div className="font-black text-lg text-white">
              {ft.home ?? 0} <span className="text-slate-500">-</span> {ft.away ?? 0}
            </div>
          ) : (
            <span className="text-xs text-slate-500">vs</span>
          )}
        </div>
        <div className="flex items-center gap-2 min-w-0 justify-end">
          <span className="font-semibold text-sm truncate text-right">{match.awayTeam?.shortName || match.awayTeam?.name}</span>
          {match.awayTeam?.crest && <img src={match.awayTeam.crest} alt="" className="w-7 h-7 object-contain" />}
        </div>
      </div>

      {p && (
        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs">
              <Zap className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-slate-400">AI Tip</span>
              <span className="text-white font-semibold">{p.best_bet?.market}: {p.best_bet?.pick}</span>
            </div>
            <span className="text-xs font-bold text-emerald-400">{p.best_bet?.confidence}%</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <ProbBar label="1" value={p.probs?.home} highlight={p.pick === "HOME"} />
            <ProbBar label="X" value={p.probs?.draw} highlight={p.pick === "DRAW"} />
            <ProbBar label="2" value={p.probs?.away} highlight={p.pick === "AWAY"} />
          </div>
        </div>
      )}
    </Link>
  );
}

function ProbBar({ label, value, highlight }) {
  return (
    <div className={`rounded-md py-1.5 text-xs ${highlight ? "bg-purple-500/20 border border-purple-500/40 text-purple-100" : "bg-white/5 text-slate-300"}`}>
      <div className="font-semibold">{label}</div>
      <div className="text-[11px] opacity-80">{value ?? 0}%</div>
    </div>
  );
}
