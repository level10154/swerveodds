import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getWorldLeagues } from "../lib/api";
import { Globe, Sparkles, Search } from "lucide-react";

export default function Leagues() {
  const [leagues, setLeagues] = useState([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all"); // all | predictions | fivedollarfootball

  useEffect(() => {
    getWorldLeagues().then((d) => setLeagues(d.leagues || [])).catch(() => {});
  }, []);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = leagues.filter((l) => {
      if (filter === "predictions" && !l.predictions) return false;
      if (filter === "fivedollarfootball" && l.source !== "fivedollarfootball") return false;
      if (!q) return true;
      return (
        (l.name || "").toLowerCase().includes(q) ||
        (l.country || "").toLowerCase().includes(q)
      );
    });
    const map = {};
    for (const l of filtered) {
      const k = l.country || "Other";
      (map[k] = map[k] || []).push(l);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [leagues, query, filter]);

  return (
    <div className="mx-auto max-w-7xl px-4 md:px-6 py-10">
      <div className="flex items-center gap-3 mb-2">
        <Globe className="w-6 h-6 text-cyan-400" />
        <h1 className="text-3xl md:text-4xl font-black tracking-tight">Worldwide Leagues</h1>
      </div>
      <p className="text-slate-400">Standings, fixtures & AI predictions from {leagues.length}+ competitions worldwide.</p>

      <div className="mt-6 flex flex-col md:flex-row md:items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search leagues or countries…"
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
          />
        </div>
        <div className="flex items-center gap-2">
          {[
            { v: "all", l: "All" },
            { v: "predictions", l: "With AI Picks" },
            { v: "fivedollarfootball", l: "Worldwide" },
          ].map((o) => (
            <button
              key={o.v}
              onClick={() => setFilter(o.v)}
              className={`px-3 py-2 rounded-md text-sm border transition ${
                filter === o.v ? "bg-purple-500/20 border-purple-500/50 text-white" : "bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              {o.l}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 space-y-8">
        {grouped.map(([country, list]) => (
          <div key={country}>
            <h2 className="text-sm uppercase tracking-wide text-slate-400 mb-3 font-semibold">{country}</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {list.map((l) => {
                const to = l.source === "football-data" ? `/league/${l.code}` : `/world-league/${l.id}`;
                return (
                  <Link key={l.id} to={to} className="nt-card rounded-xl p-4 flex items-center gap-3 transition">
                    <img
                      src={l.emblem}
                      alt=""
                      className="w-10 h-10 object-contain"
                      onError={(e) => { e.currentTarget.style.opacity = "0.2"; }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold truncate">{l.name}</div>
                      <div className="text-xs text-slate-500">{l.country}</div>
                    </div>
                    {l.predictions ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-md bg-purple-500/15 border border-purple-500/30 text-purple-200 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" /> AI
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
