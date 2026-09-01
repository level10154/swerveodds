import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Trophy, TrendingUp, Zap, ChevronRight, Star, Radio } from "lucide-react";
import { Button } from "../components/ui/button";
import MatchCard from "../components/MatchCard";
import BetOfDayCard from "../components/BetOfDayCard";
import StandingsTable from "../components/StandingsTable";
import { getPredictionsToday, getPredictionsUpcoming, getBetOfTheDay, getStandings, getCompetitions, getGlobalLive } from "../lib/api";

export default function Home() {
  const [predictions, setPredictions] = useState([]);
  const [botd, setBotd] = useState(null);
  const [standings, setStandings] = useState(null);
  const [competitions, setCompetitions] = useState([]);
  const [live, setLive] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [c, preds, liveData] = await Promise.all([
          getCompetitions().catch(() => ({ competitions: [] })),
          getPredictionsToday(4).catch(() => ({ matches: [] })),
          getGlobalLive(12).catch(() => ({ matches: [] })),
        ]);
        if (!alive) return;
        setCompetitions(c.competitions || []);
        let preview = preds.matches || [];
        // If today has few matches (season break), fall back to upcoming 14 days
        if (preview.length < 3) {
          try {
            const up = await getPredictionsUpcoming(14, 9);
            preview = up.matches || preview;
          } catch { /* ignore */ }
        }
        setPredictions(preview);
        setLive(liveData.matches || []);
        // Sequential to avoid rate limit
        const bod = await getBetOfTheDay().catch(() => null);
        if (!alive) return;
        setBotd(bod?.picks?.[0] || null);
        const st = await getStandings("PL").catch(() => null);
        if (!alive) return;
        setStandings(st);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    // Refresh live matches every 2 min
    const interval = setInterval(() => {
      getGlobalLive(12).then((d) => setLive(d.matches || [])).catch(() => {});
    }, 120000);
    return () => { alive = false; clearInterval(interval); };
  }, []);

  return (
    <div>
      {/* HERO */}
      <section className="nt-hero-bg relative overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 md:px-6 pt-16 pb-20 md:pt-24 md:pb-28 text-center">
          <span className="nt-chip inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold mb-6">
            <Sparkles className="w-3.5 h-3.5" /> Free AI Predictions · Real-time Stats
          </span>
          <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[0.95]">
            AI FOOTBALL<br />
            <span className="nt-neon-text">PREDICTIONS</span>
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-slate-400 text-lg">
            Data-driven picks from 120+ leagues. Poisson goal model + team form.
            Powered by real-time football-data.org.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link to="/bet-of-the-day"><Button size="lg" className="nt-btn-primary px-8 h-12">Get Today's Tips</Button></Link>
            <Link to="/matches"><Button size="lg" variant="outline" className="h-12 border-white/10 bg-white/5 hover:bg-white/10 text-white">Browse Matches</Button></Link>
          </div>
          <div className="mt-10 flex items-center justify-center gap-6 text-slate-400 text-sm">
            <div className="flex items-center gap-1.5"><Trophy className="w-4 h-4 text-amber-400" /> 11 Top Leagues</div>
            <div className="flex items-center gap-1.5"><Zap className="w-4 h-4 text-purple-400" /> Live Updates</div>
            <div className="flex items-center gap-1.5"><Star className="w-4 h-4 text-fuchsia-400" /> Free Forever</div>
          </div>
        </div>
      </section>

      {/* BET OF THE DAY */}
      <section className="mx-auto max-w-7xl px-4 md:px-6 -mt-10 relative z-10">
        <BetOfDayCard match={botd} loading={loading && !botd} />
      </section>

      {/* LIVE NOW */}
      {live.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 md:px-6 mt-14">
          <div className="flex items-end justify-between mb-5">
            <div>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Radio className="w-5 h-5 text-rose-400" />
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-rose-500 rounded-full animate-pulse" />
                </div>
                <h2 className="text-2xl md:text-3xl font-black tracking-tight">Live Now</h2>
                <span className="text-xs bg-rose-500/15 border border-rose-500/30 text-rose-300 px-2 py-0.5 rounded-md font-semibold">{live.length}+</span>
              </div>
              <p className="text-slate-400 text-sm mt-1">Real-time worldwide football, auto-refreshing every 2 minutes</p>
            </div>
            <Link to="/live" className="text-purple-400 text-sm hover:text-purple-300 inline-flex items-center gap-1">
              View all live <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {live.slice(0, 6).map((m) => {
              const s = m.score?.fullTime || {};
              const hs = s.home ?? 0;
              const as_ = s.away ?? 0;
              return (
                <div key={m.id} className="nt-card rounded-xl p-3 relative overflow-hidden">
                  <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] font-bold text-rose-300">
                    <span className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-pulse" /> LIVE
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-2">
                    {m.competition?.emblem && <img src={m.competition.emblem} alt="" className="w-3.5 h-3.5" onError={(e)=>{e.currentTarget.style.display='none';}} />}
                    <span className="truncate">{m.competition?.name}</span>
                  </div>
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {m.homeTeam?.crest && <img src={m.homeTeam.crest} alt="" className="w-5 h-5 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />}
                      <span className="text-sm font-semibold truncate">{m.homeTeam?.shortName || m.homeTeam?.name}</span>
                    </div>
                    <div className="text-center font-black text-lg">
                      <span className={hs > as_ ? "text-emerald-400" : ""}>{hs}</span>
                      <span className="text-slate-500 mx-1">-</span>
                      <span className={as_ > hs ? "text-emerald-400" : ""}>{as_}</span>
                    </div>
                    <div className="flex items-center gap-1.5 justify-end min-w-0">
                      <span className="text-sm font-semibold truncate text-right">{m.awayTeam?.shortName || m.awayTeam?.name}</span>
                      {m.awayTeam?.crest && <img src={m.awayTeam.crest} alt="" className="w-5 h-5 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* TODAY'S PREDICTIONS */}
      <section className="mx-auto max-w-7xl px-4 md:px-6 mt-14">
        <div className="flex items-end justify-between mb-5">
          <div>
            <h2 className="text-2xl md:text-3xl font-black tracking-tight">Upcoming AI Predictions</h2>
            <p className="text-slate-400 text-sm mt-1">Top upcoming matches (next 14 days) with 1X2, BTTS and Over/Under picks. Most European leagues resume Aug 6.</p>
          </div>
          <Link to="/predictions" className="text-purple-400 text-sm hover:text-purple-300 inline-flex items-center gap-1">
            View all <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        {loading && predictions.length === 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_,i)=>(<div key={i} className="nt-card rounded-xl h-40 animate-pulse" />))}
          </div>
        ) : predictions.length === 0 ? (
          <div className="nt-card rounded-xl p-8 text-center text-slate-400">No matches available right now. Check back soon.</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.map((m) => <MatchCard key={m.id} match={m} />)}
          </div>
        )}
      </section>

      {/* LEAGUES + STANDINGS */}
      <section className="mx-auto max-w-7xl px-4 md:px-6 mt-14 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="flex items-end justify-between mb-5">
            <div>
              <h2 className="text-2xl md:text-3xl font-black tracking-tight">Premier League Standings</h2>
              <p className="text-slate-400 text-sm mt-1">Live from football-data.org</p>
            </div>
            <Link to="/league/PL" className="text-purple-400 text-sm hover:text-purple-300 inline-flex items-center gap-1">
              Full table <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {standings ? <StandingsTable standings={standings} compact /> : <div className="nt-card rounded-xl h-64 animate-pulse" />}
        </div>
        <div>
          <div className="mb-5">
            <h2 className="text-2xl md:text-3xl font-black tracking-tight">Top Leagues</h2>
            <p className="text-slate-400 text-sm mt-1">Jump straight into any competition</p>
          </div>
          <div className="nt-card rounded-xl p-2 space-y-1">
            {competitions.map((c) => (
              <Link key={c.code} to={`/league/${c.code}`} className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-white/5">
                <div className="flex items-center gap-3 min-w-0">
                  <img src={c.emblem} alt="" className="w-6 h-6" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />
                  <div className="min-w-0">
                    <div className="text-sm font-semibold truncate">{c.name}</div>
                    <div className="text-[11px] text-slate-500">{c.country}</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="mx-auto max-w-7xl px-4 md:px-6 mt-16">
        <div className="nt-card rounded-2xl p-8 md:p-10">
          <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-2">How our predictions work</h2>
          <p className="text-slate-400 text-sm mb-6 max-w-2xl">Every prediction is generated from real, up-to-the-minute team form data — no hunches, no bias.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: TrendingUp, title: "Form & xG", desc: "We compute goals scored/conceded per game over the last 10 matches for each side." },
              { icon: Zap, title: "Poisson Model", desc: "Expected goals feed a Poisson distribution to derive 1X2, BTTS, Over/Under and correct-score probabilities." },
              { icon: Trophy, title: "Best Bet", desc: "We highlight the market with the highest probability edge — the confidence you see is the model's actual output." },
            ].map((f,i) => (
              <div key={i} className="rounded-xl bg-white/[0.03] p-5 border border-white/5">
                <f.icon className="w-6 h-6 text-purple-400 mb-3" />
                <div className="font-bold">{f.title}</div>
                <p className="text-sm text-slate-400 mt-1">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
