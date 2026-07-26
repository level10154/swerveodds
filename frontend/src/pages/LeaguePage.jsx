import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getStandings, getCompetitionMatches, getCompetitionScorers, getCompetitions } from "../lib/api";
import StandingsTable from "../components/StandingsTable";
import MatchCard from "../components/MatchCard";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";

export default function LeaguePage() {
  const { code } = useParams();
  const [tab, setTab] = useState("standings");
  const [standings, setStandings] = useState(null);
  const [matches, setMatches] = useState([]);
  const [scorers, setScorers] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      setStandings(null); setMatches([]); setScorers(null);
      try { const s = await getStandings(code); if (alive) setStandings(s); } catch(e){ /* ignore */ }
      try { const m = await getCompetitionMatches(code, "SCHEDULED"); if (alive) setMatches(m.matches || []); } catch(e){ /* ignore */ }
      try { const sc = await getCompetitionScorers(code); if (alive) setScorers(sc); } catch(e){ /* ignore */ }
    })();
    return () => { alive = false; };
  }, [code]);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-8">
      <div className="flex items-center gap-3 mb-6">
        {standings?.competition?.emblem && <img src={standings.competition.emblem} alt="" className="w-10 h-10" />}
        <div>
          <h1 className="text-3xl font-black tracking-tight">{standings?.competition?.name || code}</h1>
          <div className="text-sm text-slate-400">{standings?.area?.name}</div>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white/5">
          <TabsTrigger value="standings">Standings</TabsTrigger>
          <TabsTrigger value="fixtures">Fixtures</TabsTrigger>
          <TabsTrigger value="scorers">Top Scorers</TabsTrigger>
        </TabsList>
        <TabsContent value="standings" className="mt-6">
          {standings ? <StandingsTable standings={standings} /> : <div className="nt-card h-64 animate-pulse rounded-xl" />}
        </TabsContent>
        <TabsContent value="fixtures" className="mt-6">
          {matches.length === 0 ? (
            <div className="nt-card rounded-xl p-8 text-center text-slate-400">No upcoming fixtures available.</div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {matches.slice(0, 30).map((m) => <MatchCard key={m.id} match={m} />)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="scorers" className="mt-6">
          <ScorersTable scorers={scorers} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ScorersTable({ scorers }) {
  if (!scorers) return <div className="nt-card h-64 animate-pulse rounded-xl" />;
  const list = scorers.scorers || [];
  if (list.length === 0) return <div className="nt-card rounded-xl p-8 text-center text-slate-400">No scorer data.</div>;
  return (
    <div className="nt-card rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase text-slate-500">
          <tr>
            <th className="text-left px-4 py-2 font-medium">#</th>
            <th className="text-left px-2 py-2 font-medium">Player</th>
            <th className="text-left px-2 py-2 font-medium">Team</th>
            <th className="text-center px-2 py-2 font-medium">Goals</th>
            <th className="text-center px-2 py-2 font-medium">Assists</th>
            <th className="text-right px-4 py-2 font-medium">Played</th>
          </tr>
        </thead>
        <tbody>
          {list.map((s, i) => (
            <tr key={i} className="border-t border-white/5 hover:bg-white/[0.03]">
              <td className="px-4 py-2 text-slate-400 w-8">{i+1}</td>
              <td className="px-2 py-2 font-semibold">{s.player?.name}</td>
              <td className="px-2 py-2 text-slate-300">
                <div className="flex items-center gap-2">
                  {s.team?.crest && <img src={s.team.crest} alt="" className="w-5 h-5" />}
                  <span>{s.team?.shortName || s.team?.name}</span>
                </div>
              </td>
              <td className="px-2 py-2 text-center font-bold text-emerald-400">{s.goals}</td>
              <td className="px-2 py-2 text-center text-slate-300">{s.assists ?? "-"}</td>
              <td className="px-4 py-2 text-right text-slate-400">{s.playedMatches ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
