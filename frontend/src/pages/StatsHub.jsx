import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCompetitions, getStandings } from "../lib/api";
import { BarChart3 } from "lucide-react";

export default function StatsHub() {
  const [comps, setComps] = useState([]);
  const [selected, setSelected] = useState("PL");
  const [standings, setStandings] = useState(null);

  useEffect(() => {
    getCompetitions().then((c) => setComps(c.competitions || [])).catch(() => {});
  }, []);

  useEffect(() => {
    setStandings(null);
    getStandings(selected).then(setStandings).catch(() => {});
  }, [selected]);

  const homeTable = standings?.standings?.find((s) => s.type === "HOME")?.table || [];
  const awayTable = standings?.standings?.find((s) => s.type === "AWAY")?.table || [];

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <div className="flex items-center gap-3 mb-2">
        <BarChart3 className="w-6 h-6 text-cyan-400" />
        <h1 className="text-3xl md:text-4xl font-black tracking-tight">Stats Hub</h1>
      </div>
      <p className="text-slate-400">Team stats, home/away splits & league-by-league tables.</p>

      <div className="mt-6 flex items-center gap-2 flex-wrap">
        {comps.map((c) => (
          <button key={c.code} onClick={() => setSelected(c.code)}
            className={`px-3 py-1.5 rounded-md text-sm border transition inline-flex items-center gap-2 ${
              selected === c.code ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
            }`}>
            <img src={c.emblem} alt="" className="w-4 h-4" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />
            {c.name}
          </button>
        ))}
      </div>

      {standings ? (
        <div className="mt-8 grid lg:grid-cols-2 gap-6">
          <SplitTable title="Home form table" rows={homeTable} accent="emerald" />
          <SplitTable title="Away form table" rows={awayTable} accent="fuchsia" />
        </div>
      ) : (
        <div className="mt-8 nt-card h-64 rounded-xl animate-pulse" />
      )}
    </div>
  );
}

function SplitTable({ title, rows, accent }) {
  return (
    <div className="nt-card rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5 font-bold text-sm">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[11px] uppercase text-slate-500">
            <tr>
              <th className="text-left px-4 py-2">#</th>
              <th className="text-left px-2 py-2">Team</th>
              <th className="text-center px-2 py-2">P</th>
              <th className="text-center px-2 py-2">W-D-L</th>
              <th className="text-center px-2 py-2">GF-GA</th>
              <th className="text-right px-4 py-2">Pts</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0,10).map((r) => (
              <tr key={r.team.id} className="border-t border-white/5">
                <td className="px-4 py-2 text-slate-400 w-8">{r.position}</td>
                <td className="px-2 py-2">
                  <div className="flex items-center gap-2">
                    {r.team.crest && <img src={r.team.crest} alt="" className="w-5 h-5" />}
                    <span className="truncate">{r.team.shortName || r.team.name}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-center text-slate-300">{r.playedGames}</td>
                <td className="px-2 py-2 text-center text-slate-300">{r.won}-{r.draw}-{r.lost}</td>
                <td className="px-2 py-2 text-center text-slate-300">{r.goalsFor}-{r.goalsAgainst}</td>
                <td className="px-4 py-2 text-right font-bold">{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
