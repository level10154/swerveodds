import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCompetitions } from "../lib/api";

export default function Leagues() {
  const [comps, setComps] = useState([]);
  useEffect(() => { getCompetitions().then((c) => setComps(c.competitions || [])).catch(() => {}); }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <h1 className="text-3xl md:text-4xl font-black tracking-tight">Football Leagues</h1>
      <p className="text-slate-400 mt-1">Standings, fixtures and top scorers from major competitions worldwide.</p>

      <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {comps.map((c) => (
          <Link key={c.code} to={`/league/${c.code}`} className="nt-card rounded-xl p-5 flex items-center gap-4 transition">
            <img src={c.emblem} alt="" className="w-14 h-14 object-contain" onError={(e)=>{e.currentTarget.style.opacity='0.2';}} />
            <div>
              <div className="font-bold text-lg">{c.name}</div>
              <div className="text-sm text-slate-400">{c.country}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
