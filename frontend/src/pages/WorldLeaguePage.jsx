import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getWorldLeagueNext, getWorldLeagueTable } from "../lib/api";
import MatchCard from "../components/MatchCard";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Globe, Info } from "lucide-react";

export default function WorldLeaguePage() {
  const { ref } = useParams();
  const [data, setData] = useState(null);
  const [table, setTable] = useState(null);
  const [tab, setTab] = useState("fixtures");
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    let alive = true;
    setData(null); setTable(null); setErrored(false);
    // Client-side timeout guard: never leave the page on an infinite skeleton
    // even if the origin call is unusually slow - always resolve to an empty,
    // renderable shape instead.
    const withTimeout = (p, ms) => Promise.race([
      p,
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms)),
    ]);
    withTimeout(getWorldLeagueNext(ref), 30000)
      .then((d) => { if (alive) setData(d); })
      .catch(() => { if (alive) { setErrored(true); setData({ league: {}, upcoming: [], recent: [] }); } });
    withTimeout(getWorldLeagueTable(ref), 30000)
      .then((t) => { if (alive) setTable(t); })
      .catch(() => { if (alive) setTable({ league: {}, table: [] }); });
    return () => { alive = false; };
  }, [ref]);

  if (!data) return <div className="mx-auto max-w-5xl px-4 py-10"><div className="nt-card rounded-2xl h-64 animate-pulse" /></div>;

  const l = data.league || {};

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-8">
      <div className="flex items-center gap-4 mb-6">
        <img src={l.badge || l.logo} alt="" className="w-14 h-14 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />
        <div>
          <h1 className="text-3xl font-black tracking-tight">{l.name}</h1>
          <div className="text-sm text-slate-400">{l.country} · Season {l.currentSeason}</div>
        </div>
      </div>

      {l.description && (
        <div className="nt-card rounded-xl p-4 mb-6 text-sm text-slate-300 leading-relaxed">
          {l.description.slice(0, 400)}{l.description.length > 400 ? "…" : ""}
        </div>
      )}

      <div className="nt-card rounded-lg p-3 mb-4 text-xs text-slate-400 flex items-start gap-2">
        <Info className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
        <div>Powered by 5DollarFootballAPI. Standings aren't available on this plan yet; upgrade for full schedules and tables. Predictions not available for this league.</div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white/5">
          <TabsTrigger value="fixtures">Upcoming</TabsTrigger>
          <TabsTrigger value="recent">Recent Results</TabsTrigger>
          <TabsTrigger value="table">Table</TabsTrigger>
        </TabsList>

        <TabsContent value="fixtures" className="mt-6">
          {data.upcoming.length === 0 ? (
            <div className="nt-card rounded-xl p-8 text-center text-slate-400">No upcoming fixtures available.</div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.upcoming.map((m) => <MatchCard key={m.id} match={m} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="recent" className="mt-6">
          {data.recent.length === 0 ? (
            <div className="nt-card rounded-xl p-8 text-center text-slate-400">No recent results available.</div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.recent.map((m) => <MatchCard key={m.id} match={m} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="table" className="mt-6">
          {!table ? (
            <div className="nt-card rounded-xl h-64 animate-pulse" />
          ) : (table.table || []).length === 0 ? (
            <div className="nt-card rounded-xl p-8 text-center text-slate-400">Standings not available for this league yet.</div>
          ) : (
            <div className="nt-card rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead className="text-[11px] uppercase text-slate-500">
                  <tr>
                    <th className="text-left px-4 py-2">#</th>
                    <th className="text-left px-2 py-2">Team</th>
                    <th className="text-center px-2 py-2">P</th>
                    <th className="text-center px-2 py-2">W-D-L</th>
                    <th className="text-center px-2 py-2">GD</th>
                    <th className="text-right px-4 py-2">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {table.table.map((r, i) => (
                    <tr key={i} className="border-t border-white/5">
                      <td className="px-4 py-2 text-slate-400 w-8">{r.position}</td>
                      <td className="px-2 py-2">
                        <div className="flex items-center gap-2">
                          {r.team.crest && <img src={r.team.crest} alt="" className="w-5 h-5" />}
                          <span>{r.team.name}</span>
                        </div>
                      </td>
                      <td className="px-2 py-2 text-center text-slate-300">{r.playedGames}</td>
                      <td className="px-2 py-2 text-center text-slate-300">{r.won}-{r.draw}-{r.lost}</td>
                      <td className="px-2 py-2 text-center text-slate-300">{r.goalDifference}</td>
                      <td className="px-4 py-2 text-right font-bold">{r.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
