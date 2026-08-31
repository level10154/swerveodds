# ⚡ NerdyStats — The Global Football Predictions Engine

> *NerdyTips' neon swagger meets StatsHub's stat-nerd brain — reborn as one blazing-fast, AI-free prediction platform.*

Live scores ticking in real time. Poisson-powered predictions that actually explain their math. Leagues from São Paulo to Seoul. All wrapped in a dark, neon-lit interface built for people who watch football like it's a spreadsheet with a heartbeat.

---

## 🧭 What Is This?

NerdyStats is a full-stack football intelligence platform that fuses two worlds:

- **NerdyTips' DNA** → punchy "Bet of the Day" picks, confidence scores, dark neon aesthetics.
- **StatsHub's DNA** → deep team form, standings tables, goal models, correct-score probabilities.

No black-box AI hype, no vague "our algorithm says so." Every prediction traces back to a transparent **Poisson distribution model** fed by real recent-form data — goals scored, goals conceded, points-per-game, and head-to-head trends — pulled live from three independent football data providers.

---

## 🌍 The Data Trinity

Three APIs, one unified feed, zero single point of failure:

| Source | Role | Coverage |
|---|---|---|
| ⚽ **football-data.org** | Core predictions engine, standings, scorers | Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League + top European competitions |
| 🌐 **TheSportsDB** | Worldwide league discovery + team badges/crests | 18+ curated global leagues, free & keyless |
| 🔥 **SportApi7 (via RapidAPI)** | Live worldwide scores, extended global predictions | 5,000+ leagues — Allsvenskan, Chinese Super League, K League 1, Swiss Super League, and beyond |

Everything is deduplicated, normalized into a single match schema, and cached aggressively in **MongoDB** so we never blow through a provider's rate limit or monthly quota — even when the whole internet is refreshing live scores during a Champions League final.

---

## 🧠 How the Predictions Actually Work

`predictor.py` is the brain. No LLM, no vibes — just math you can audit:

1. **Form extraction** — last 10 finished matches per team → average goals scored/conceded, PPG, BTTS%, Over 2.5%, and a W/D/L form string.
2. **Expected goals (λ)** — blends a team's attacking output with the opponent's defensive leakiness, plus a `+0.35` home-advantage boost.
3. **Poisson goal matrix** — simulates every scoreline from 0-0 to 6-6, deriving:
   - **1X2 probabilities** (Home / Draw / Away)
   - **BTTS Yes/No**
   - **Over/Under 1.5, 2.5, 3.5 goals**
   - **Top 5 most likely correct scores**
4. **Best Bet selector** — compares the edge across 1X2, Over 2.5, and BTTS markets and surfaces the single highest-confidence pick as the "Bet of the Day."

The same engine runs twice — once against `football-data.org` fixtures, once against `SportApi7` global fixtures — so a K League 1 derby gets the exact same statistical rigor as a Champions League final.

> 🔮 **On the roadmap:** wiring in **Ollama** to generate natural-language reasoning/commentary on top of these numbers (e.g. *"Arsenal have won 4 of their last 5 at home and conceded just twice — the model leans Home + Over 2.5."*).

---

## 🏗️ Architecture

```
                     ┌─────────────────────┐
                     │   React Frontend     │
                     │  (Tailwind + Shadcn) │
                     └──────────┬───────────┘
                                │ REST (/api/**)
                     ┌──────────▼───────────┐
                     │   FastAPI Backend     │
                     │     server.py         │
                     └───┬──────┬────────┬───┘
             ┌───────────┘      │        └────────────┐
             ▼                  ▼                     ▼
   football_api.py        sports_db.py          api_football.py
   (football-data.org)   (TheSportsDB)          (SportApi7/RapidAPI)
             │                  │                     │
             └──────────────────┼─────────────────────┘
                                ▼
                         predictor.py
                    (Poisson prediction engine)
                                │
                                ▼
                         MongoDB (Motor)
                  aggressive TTL caching layer
```

### Backend — `FastAPI` + `Motor` (async MongoDB)

| File | Responsibility |
|---|---|
| `server.py` | Route definitions, match serialization, prediction orchestration |
| `football_api.py` | football-data.org adapter — matches, standings, scorers, team history |
| `sports_db.py` | TheSportsDB adapter — worldwide leagues, tables, badges |
| `api_football.py` | SportApi7 adapter — live events, tournaments, team form, quota-safe fallbacks |
| `predictor.py` | The Poisson prediction engine described above |

### Frontend — `React 19` + `Tailwind CSS` + `Shadcn UI`

| Page | Purpose |
|---|---|
| `Home.jsx` | Hero, live ticker, top predictions preview |
| `AllMatches.jsx` | Full fixture list across leagues |
| `Predictions.jsx` | AI-style prediction feed (1X2, BTTS, O/U) |
| `MatchDetail.jsx` | Deep-dive stats for a single fixture |
| `LeaguePage.jsx` / `WorldLeaguePage.jsx` | Standings + fixtures per competition |
| `StatsHub.jsx` | Statistical dashboards |
| `Leagues.jsx` | Global league directory |
| `BetOfDay.jsx` | The single highest-confidence pick of the day |
| `LiveMatches.jsx` | Real-time worldwide scoreboard |

---

## 📡 API Reference

**Predictions (football-data.org powered)**
```
GET /api/predictions/today
GET /api/predictions/upcoming?days=14&limit=24
GET /api/predictions/bet-of-the-day
GET /api/match/{match_id}
```

**Global / Worldwide (SportApi7 powered)**
```
GET /api/global/live
GET /api/global/tournaments
GET /api/global/tournament/{tid}/standings
GET /api/global/tournament/{tid}/events
GET /api/global/predictions/tournament/{tid}
GET /api/global/predictions/live
GET /api/global/predictions/upcoming
```

**Leagues, Standings & Matches**
```
GET /api/competitions
GET /api/world/leagues
GET /api/world/matches/today
GET /api/world/league/{league_ref}/next
GET /api/world/league/{league_ref}/table
GET /api/standings/{comp_code}
GET /api/matches/today
GET /api/matches/range?date_from=&date_to=
GET /api/competition/{comp_code}/matches
GET /api/competition/{comp_code}/scorers
```

**Health**
```
GET /api/apif/status   # SportApi7 subscription/quota health check
```

---

## 🎨 Design Language

Dark neon, stat-nerd energy:

- **Base**: near-black backgrounds with layered depth (glassmorphism cards, subtle grain).
- **Accents**: sharp neon highlights for live scores, confidence bars, and "Bet of the Day" callouts.
- **Motion**: micro-animations on hover, staggered reveals on prediction cards, pulsing dots for live matches.
- **Typography**: bold, high-contrast headers for scannability during matchday chaos.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, React Router 7, Tailwind CSS, Shadcn/Radix UI, Framer Motion, Recharts |
| Backend | FastAPI, Python 3, HTTPX (async), Motor (async MongoDB driver) |
| Database | MongoDB — match cache, standings cache, prediction cache (TTL-based) |
| External APIs | football-data.org, TheSportsDB, SportApi7 (RapidAPI) |

---

## ⚙️ Environment Variables

**Backend** (`/app/backend/.env`)
```
MONGO_URL=              # MongoDB connection string
DB_NAME=                # Database name
CORS_ORIGINS=           # Allowed CORS origins
FOOTBALL_DATA_API_KEY=  # football-data.org API key
RAPIDAPI_KEY=           # SportApi7 (RapidAPI) key
THESPORTSDB_KEY=        # TheSportsDB key (optional — free tier works without one)
```

**Frontend** (`/app/frontend/.env`)
```
REACT_APP_BACKEND_URL=  # Public backend URL (all API calls route through this)
```

---

## 🚦 Running Locally

Services are supervisor-managed — hot reload is already active for both frontend and backend.

```bash
# Check status
sudo supervisorctl status

# Restart after .env or dependency changes
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Backend logs
tail -n 100 /var/log/supervisor/backend.err.log
```

Frontend → `http://localhost:3000` · Backend → `http://localhost:8001/api`

---

## ⚠️ Known Constraints

- **SportApi7 Basic quota**: The free RapidAPI tier has a monthly cap. When exhausted, endpoints gracefully fall back to MongoDB cache instead of erroring out — global/live pages may show slightly stale data until the quota resets or the plan is upgraded.
- **European summer break**: Major European leagues pause seasonally. Prediction endpoints look ahead up to 30 days to always surface the next real fixtures.
- **Team badge CDN quirks**: Some SofaScore-hosted crests block direct hotlinking (403); the UI falls back to auto-generated `ui-avatars.com` badges for those teams.

---

## 🔮 What's Next

- [ ] **Ollama integration** — natural-language reasoning layered on top of the statistical picks.
- [ ] SportApi7 quota upgrade/fallback hardening for uninterrupted global coverage.

---

Built with real data, real math, and zero patience for vague predictions. ⚡
