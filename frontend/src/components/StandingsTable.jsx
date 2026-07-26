export default function StandingsTable({ standings, compact = false }) {
  if (!standings) return null;
  const table = standings.standings?.find((s) => s.type === "TOTAL")?.table || [];
  const rows = compact ? table.slice(0, 8) : table;
  return (
    <div className="nt-card rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {standings.competition?.emblem && <img src={standings.competition.emblem} alt="" className="w-6 h-6" />}
          <div>
            <div className="font-bold text-sm">{standings.competition?.name}</div>
            <div className="text-[11px] text-slate-400">Season {standings.filters?.season || standings.season?.startDate?.slice(0,4)}</div>
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[11px] uppercase text-slate-500">
            <tr>
              <th className="text-left px-4 py-2 font-medium">#</th>
              <th className="text-left px-2 py-2 font-medium">Team</th>
              <th className="text-center px-2 py-2 font-medium">PL</th>
              {!compact && <th className="text-center px-2 py-2 font-medium">W</th>}
              {!compact && <th className="text-center px-2 py-2 font-medium">D</th>}
              {!compact && <th className="text-center px-2 py-2 font-medium">L</th>}
              <th className="text-center px-2 py-2 font-medium">GD</th>
              <th className="text-right px-4 py-2 font-medium">PTS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.team.id} className="border-t border-white/5 hover:bg-white/[0.03]">
                <td className="px-4 py-2 text-slate-400 w-8">{r.position}</td>
                <td className="px-2 py-2">
                  <div className="flex items-center gap-2">
                    {r.team.crest && <img src={r.team.crest} alt="" className="w-5 h-5" />}
                    <span className="truncate">{r.team.shortName || r.team.name}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-center text-slate-300">{r.playedGames}</td>
                {!compact && <td className="px-2 py-2 text-center text-slate-300">{r.won}</td>}
                {!compact && <td className="px-2 py-2 text-center text-slate-300">{r.draw}</td>}
                {!compact && <td className="px-2 py-2 text-center text-slate-300">{r.lost}</td>}
                <td className={`px-2 py-2 text-center ${r.goalDifference > 0 ? "text-emerald-400" : r.goalDifference < 0 ? "text-rose-400" : "text-slate-300"}`}>
                  {r.goalDifference > 0 ? `+${r.goalDifference}` : r.goalDifference}
                </td>
                <td className="px-4 py-2 text-right font-bold">{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
