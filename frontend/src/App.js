import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import AllMatches from "./pages/AllMatches";
import Predictions from "./pages/Predictions";
import MatchDetail from "./pages/MatchDetail";
import LeaguePage from "./pages/LeaguePage";
import Leagues from "./pages/Leagues";
import WorldLeaguePage from "./pages/WorldLeaguePage";
import LiveMatches from "./pages/LiveMatches";
import StatsHub from "./pages/StatsHub";
import BetOfDay from "./pages/BetOfDay";

function App() {
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/matches" element={<AllMatches />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/bet-of-the-day" element={<BetOfDay />} />
          <Route path="/leagues" element={<Leagues />} />
          <Route path="/league/:code" element={<LeaguePage />} />
          <Route path="/world-league/:ref" element={<WorldLeaguePage />} />
          <Route path="/live" element={<LiveMatches />} />
          <Route path="/stats" element={<StatsHub />} />
          <Route path="/match/:id" element={<MatchDetail />} />
        </Routes>
        <Footer />
      </BrowserRouter>
    </div>
  );
}

export default App;
