import { useEffect, useState } from "react";
import { getBetOfTheDay } from "../lib/api";
import BetOfDayCard from "../components/BetOfDayCard";
import { FormPills, ProbBarLine } from "../components/PredictionParts";
import { Zap } from "lucide-react";

export default function BetOfDay() {
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBetOfTheDay().then((x) => setPicks(x?.picks || [])).catch(() => setPicks([])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 md:px-6 py-10">
      <h1 className="text-3xl md:text-4xl font-black tracking-tight">Bet of the Day</h1>
      <p className="text-slate-400 mt-1">Our highest-confidence picks from today's fixtures (60%+ confidence).</p>

      {loading ? (
        <div className="mt-6"><BetOfDayCard match={null} loading /></div>
      ) : picks.length === 0 ? (
        <div className="mt-6"><BetOfDayCard match={null} loading={false} /></div>
      ) : (
        picks.map((m, i) => (
          <div key={m.id} className="mt-6">
            {picks.length > 1 && (
              <div className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">Pick #{i + 1}</div>
            )}
            <BetOfDayCard match={m} loading={false} />
            {m?.prediction && (
              <div className="nt-card rounded-2xl p-6 mt-4">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="w-5 h-5 text-purple-400" />
                  <h2 className="font-bold">Why this pick?</h2>
                </div>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <div className="text-sm font-semibold mb-2">{m.homeTeam.name} · last 10</div>
                    <FormPills form={m.prediction.home_form.form} />
                    <div className="mt-3 text-xs text-slate-400">PPG {m.prediction.home_form.ppg} · GF {m.prediction.home_form.gs_avg} · GA {m.prediction.home_form.gc_avg}</div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold mb-2">{m.awayTeam.name} · last 10</div>
                    <FormPills form={m.prediction.away_form.form} />
                    <div className="mt-3 text-xs text-slate-400">PPG {m.prediction.away_form.ppg} · GF {m.prediction.away_form.gs_avg} · GA {m.prediction.away_form.gc_avg}</div>
                  </div>
                </div>
                <div className="mt-5 grid md:grid-cols-2 gap-x-6 gap-y-3">
                  <ProbBarLine label="Home Win" value={m.prediction.probs.home} />
                  <ProbBarLine label="Away Win" value={m.prediction.probs.away} />
                  <ProbBarLine label="Over 2.5 Goals" value={m.prediction.probs.over_25} color="bg-emerald-500" />
                  <ProbBarLine label="BTTS Yes" value={m.prediction.probs.btts_yes} color="bg-fuchsia-500" />
                </div>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
