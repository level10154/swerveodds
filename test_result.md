#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Combine nerdytips.com + statshub.com into one free AI football prediction site using real-time football-data.org API (key provided). Predictions computed from team form + Poisson goal model. Dark neon design (NerdyTips-style) with stats tables/standings (StatsHub-style)."

backend:
  - task: "Football-data.org integration with MongoDB cache & 10 req/min rate limiter"
    implemented: true
    working: true
    file: "/app/backend/football_api.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Client uses X-Auth-Token, MongoDB caching (5-30min TTL per endpoint kind), 6.5s spacing between live calls, stale-if-error fallback. Env loaded from .env inside module."
      - working: true
        agent: "testing"
        comment: "All calls succeed; cache serves subsequent requests instantly."

  - task: "Prediction engine (Poisson + form-based 1X2/BTTS/Over/Under/correct-score) with per-match cache"
    implemented: true
    working: true
    file: "/app/backend/predictor.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Poisson matrix from team form; added per-match prediction cache (15 min TTL) to make bulk endpoints fast."
      - working: true
        agent: "testing"
        comment: "Real team form → valid probabilities (0-100), best_bet consistent."

  - task: "API routes"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "10/10 tests passed: /competitions, /matches/today, /predictions/today, /predictions/upcoming, /predictions/bet-of-the-day, /standings/PL, /competition/PL/matches, /competition/PL/scorers, /match/{id}, cache verification."

frontend:
  - task: "Home, All Matches, Predictions, Bet of the Day, League, Stats Hub, Leagues, Match Detail pages with dark neon UI"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Visually verified via screenshots — hero, bet-of-day card, prediction cards with 1X2/BTTS/Over-Under, standings tables, league tabs (standings/fixtures/scorers) all render with real data."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "API routes: /api/competitions, /matches/today, /matches/range, /predictions/today, /predictions/upcoming, /predictions/bet-of-the-day, /match/{id}, /standings/{code}, /competition/{code}/matches, /competition/{code}/scorers"
    - "Football-data.org integration with MongoDB cache & 10 req/min rate limiter"
    - "Prediction engine (Poisson + form-based 1X2/BTTS/Over/Under/correct-score)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Full-stack app is up. Please validate backend endpoints only (frontend is stable):
      Base URL: http://localhost:8001
      1. GET /api/competitions – expect { competitions: [11 items with code/name/country/emblem] }
      2. GET /api/matches/today – expect matches array (may be small in low season windows; verify structure)
      3. GET /api/predictions/today?limit=3 – each match has `prediction` with keys: probs (home/draw/away/btts_yes/over_25 …), top_scores, most_likely_score, pick, confidence, best_bet
      4. GET /api/predictions/bet-of-the-day – single match object with prediction
      5. GET /api/standings/PL – expects standings.standings[TOTAL].table[20 items]
      6. GET /api/competition/PL/scorers – top scorers list
      7. GET /api/match/{id} using an id from /matches/today
      Notes:
      - Rate limit is 10 req/min on football-data.org; cache is aggressive. Testing agent should avoid tight loops. Please sleep >=7s between calls to distinct uncached endpoints.
      - Predictions require 2 additional team-match calls per match. First call warms cache; subsequent are instant.
      - There is NO auth on any endpoint.
