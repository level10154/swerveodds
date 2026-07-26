import { Link } from "react-router-dom";
import { Github, Twitter, Send } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 mt-16">
      <div className="mx-auto max-w-7xl px-4 md:px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="col-span-2 md:col-span-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 via-fuchsia-500 to-blue-500 flex items-center justify-center font-black text-white">N</div>
            <span className="font-black text-lg tracking-tight">NERDYSTATS</span>
          </div>
          <p className="mt-3 text-sm text-slate-400">Free AI football predictions & real-time stats from 120+ leagues.</p>
          <div className="mt-4 flex items-center gap-3 text-slate-400">
            <Twitter className="w-4 h-4 hover:text-white cursor-pointer" />
            <Send className="w-4 h-4 hover:text-white cursor-pointer" />
            <Github className="w-4 h-4 hover:text-white cursor-pointer" />
          </div>
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">Predictions</div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li><Link to="/bet-of-the-day">Bet of the Day</Link></li>
            <li><Link to="/predictions">Today's Tips</Link></li>
            <li><Link to="/matches">All Matches</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">Stats Hub</div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li><Link to="/stats">Standings</Link></li>
            <li><Link to="/leagues">Leagues</Link></li>
            <li><Link to="/stats">Top Scorers</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">Company</div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>How it works</li>
            <li>Blog</li>
            <li>Contact</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/5">
        <div className="mx-auto max-w-7xl px-4 md:px-6 py-4 flex items-center justify-between text-xs text-slate-500">
          <span>© {new Date().getFullYear()} NerdyStats. For entertainment only. 18+.</span>
          <span>Data by football-data.org</span>
        </div>
      </div>
    </footer>
  );
}
