import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X, Zap, Trophy, Calendar, Sparkles, Search, Radio } from "lucide-react";
import { Button } from "./ui/button";

const navItems = [
  { to: "/live", label: "Live Now", icon: Radio },
  { to: "/bet-of-the-day", label: "Bet of the Day", icon: Sparkles },
  { to: "/matches", label: "All Matches", icon: Calendar },
  { to: "/predictions", label: "Predictions", icon: Zap },
  { to: "/leagues", label: "Leagues", icon: Trophy },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-[#05060d]/85 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 md:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 via-fuchsia-500 to-blue-500 flex items-center justify-center font-black text-white">N</div>
          <span className="font-black tracking-tight text-lg">
            NERDY<span className="text-purple-400">STATS</span>
          </span>
        </Link>
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              className={({ isActive }) =>
                `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive ? "text-white bg-white/5" : "text-slate-300 hover:text-white hover:bg-white/5"
                }`
              }
            >
              {it.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <button className="hidden md:flex items-center gap-2 text-sm text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 px-3 py-2 rounded-md">
            <Search className="w-4 h-4" /> <span className="text-slate-400">Search</span>
          </button>
          <Button className="nt-btn-primary hidden md:inline-flex">Get Started</Button>
          <button className="md:hidden text-slate-200" onClick={() => setOpen(!open)}>
            {open ? <X /> : <Menu />}
          </button>
        </div>
      </div>
      {open && (
        <div className="md:hidden border-t border-white/5 bg-[#05060d]">
          <div className="px-4 py-3 flex flex-col gap-1">
            {navItems.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-md text-sm ${
                    isActive ? "text-white bg-white/10" : "text-slate-300 hover:bg-white/5"
                  }`
                }
              >
                <it.icon className="w-4 h-4" /> {it.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
