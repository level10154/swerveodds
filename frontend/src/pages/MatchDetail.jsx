import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMatch } from "../lib/api";
import { FormPills, ProbBarLine } from "../components/PredictionParts";
import { ChevronLeft, Zap, Target, Trophy, Clock } from "lucide-react";

export default function MatchDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try { const d = await getMatch(id); if (alive) setData(d); }
      catch(e){ if(alive) setData({ error: e?.response?.data?.detail || "Failed to load" }); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [id]);

  if (loading) return <div className="mx-auto max-w-5xl px-4 py-10"><div className="nt-card rounded-2xl h-96 animate-pulse" /></div>;
  if (!data || data.error) return <div className="mx-auto max-w-5xl px-4 py-10 text-slate-400">Match not found. <Link to="/matches" className="text-purple-400">Back</Link></div>;

  const m = data;
  const p = m.prediction;
  const kickoff = new Date(m.utcDate);

  return (
    <div className="mx-auto max-w-5xl px-4 md:px-6 py-8">
      <Link to="/matches" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-4"><ChevronLeft className="w-4 h-4" /> Back to matches</Link>

      <div className="nt-card rounded-2xl p-6 md:p-8 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-purple-600/15 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-6">
            {m.competition?.emblem && <img src={m.competition.emblem} alt="" className="w-5 h-5" />}
            <span>{m.competition?.name}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {kickoff.toLocaleString([], { weekday:"short", month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" })}</span>
            {m.matchday && <><span>·</span><span>MD {m.matchday}</span></>}
          </div>

          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
            <div className="flex flex-col items-center text-center gap-3">
              {m.homeTeam?.crest && <img src={m.homeTeam.crest} alt="" className="w-20 h-20 object-contain" />}
              <div>
                <div className="font-bold text-lg">{m.homeTeam?.name}</div>
                <div className="mt-2"><FormPills form={p?.home_form?.form} /></div>
              </div>
            </div>
            <div className="text-center">
              {m.status === "FINISHED" || m.status === "IN_PLAY" ? (
                <div className="text-5xl font-black">{m.score?.fullTime?.home ?? 0} <span className="text-slate-600">-</span> {m.score?.fullTime?.away ?? 0}</div>
              ) : (
                <div className="text-4xl font-black text-white/70">VS</div>
              )}
              <div className="text-xs text-slate-400 mt-1">{m.status.replace("_"," ")}</div>
            </div>
            <div className="flex flex-col items-center text-center gap-3">
              {m.awayTeam?.crest && <img src={m.awayTeam.crest} alt="" className="w-20 h-20 object-contain" />}
              <div>
                <div className="font-bold text-lg">{m.awayTeam?.name}</div>
                <div className="mt-2"><FormPills form={p?.away_form?.form} /></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {p && (
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          <div className="nt-card rounded-xl p-5 md:col-span-2">
            <div className="flex items-center gap-2 mb-4"><Zap className="w-5 h-5 text-purple-400" /><h2 className="font-bold">Match Probabilities</h2></div>
            <div className="grid grid-cols-3 gap-3 mb-5">
              <ProbBox label="Home Win" value={p.probs.home} highlight={p.pick === "HOME"} />
              <ProbBox label="Draw" value={p.probs.draw} highlight={p.pick === "DRAW"} />
              <ProbBox label="Away Win" value={p.probs.away} highlight={p.pick === "AWAY"} />
            </div>
            <div className="grid md:grid-cols-2 gap-x-6 gap-y-3">
              <ProbBarLine label="Over 1.5 Goals" value={p.probs.over_15} color="bg-emerald-500" />
              <ProbBarLine label="Over 2.5 Goals" value={p.probs.over_25} color="bg-emerald-500" />
              <ProbBarLine label="Over 3.5 Goals" value={p.probs.over_35} color="bg-emerald-400" />
              <ProbBarLine label="BTTS Yes" value={p.probs.btts_yes} color="bg-fuchsia-500" />
              <ProbBarLine label="BTTS No" value={p.probs.btts_no} color="bg-slate-500" />
              <ProbBarLine label="Under 2.5 Goals" value={p.probs.under_25} color="bg-slate-500" />
            </div>
          </div>

          <div className="nt-card rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4"><Target className="w-5 h-5 text-fuchsia-400" /><h2 className="font-bold">Best Bet</h2></div>
            <div className="rounded-lg bg-purple-500/10 border border-purple-500/30 p-4">
              <div className="text-xs uppercase text-purple-300">Recommended</div>
              <div className="font-bold mt-1">{p.best_bet.market}: {p.best_bet.pick}</div>
              <div className="text-3xl font-black text-emerald-400 mt-2">{p.best_bet.confidence}%</div>
              <div className="text-xs text-slate-400">confidence</div>
            </div>
            <div className="mt-4">
              <div className="text-xs uppercase text-slate-400 mb-2">Top Correct Scores</div>
              <div className="space-y-1.5">
                {p.top_scores.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">{s.score}</span>
                    <span className="text-white font-semibold">{s.prob}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="nt-card rounded-xl p-5 md:col-span-3">
            <div className="flex items-center gap-2 mb-4"><Trophy className="w-5 h-5 text-amber-400" /><h2 className="font-bold">Recent Form (Last 10)</h2></div>
            <div className="grid md:grid-cols-2 gap-6">
              <TeamFormBlock name={m.homeTeam?.name} data={p.home_form} />
              <TeamFormBlock name={m.awayTeam?.name} data={p.away_form} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProbBox({ label, value, highlight }) {
  return (
    <div className={`rounded-lg p-4 text-center ${highlight ? "bg-purple-500/20 border border-purple-500/40" : "bg-white/5"}`}>
      <div className="text-[11px] uppercase text-slate-400">{label}</div>
      <div className={`text-3xl font-black mt-1 ${highlight ? "text-white" : "text-slate-200"}`}>{value}%</div>
    </div>
  );
}

function TeamFormBlock({ name, data }) {
  if (!data) return null;
  return (
    <div>
      <div className="font-semibold mb-2">{name}</div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-white/5 p-3"><div className="text-[10px] uppercase text-slate-400">PPG</div><div className="font-black text-xl">{data.ppg}</div></div>
        <div className="rounded-lg bg-white/5 p-3"><div className="text-[10px] uppercase text-slate-400">Goals For</div><div className="font-black text-xl">{data.gs_avg}</div></div>
        <div className="rounded-lg bg-white/5 p-3"><div className="text-[10px] uppercase text-slate-400">Goals Against</div><div className="font-black text-xl">{data.gc_avg}</div></div>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <div>W {data.wins} · D {data.draws} · L {data.losses}</div>
        <div>BTTS {data.btts_pct}% · O2.5 {data.over25_pct}%</div>
      </div>
    </div>
  );
}
