import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 30000 });

export const getCompetitions = () => api.get("/competitions").then(r => r.data);
export const getWorldLeagues = () => api.get("/world/leagues").then(r => r.data);
export const getWorldMatchesToday = () => api.get("/world/matches/today").then(r => r.data);
export const getWorldLeagueNext = (ref) => api.get(`/world/league/${ref}/next`).then(r => r.data);
export const getWorldLeagueTable = (ref) => api.get(`/world/league/${ref}/table`).then(r => r.data);
export const getApifStatus = () => api.get("/apif/status").then(r => r.data);
export const getApifFixtures = (date) => api.get(`/apif/fixtures?date=${date}`).then(r => r.data);
export const getPredictionsToday = (limit = 12) => api.get(`/predictions/today?limit=${limit}`).then(r => r.data);
export const getPredictionsUpcoming = (days = 3, limit = 20) => api.get(`/predictions/upcoming?days=${days}&limit=${limit}`).then(r => r.data);
export const getBetOfTheDay = () => api.get("/predictions/bet-of-the-day").then(r => r.data);
export const getMatchesToday = (withPrediction = false) => api.get(`/matches/today?with_prediction=${withPrediction}`).then(r => r.data);
export const getMatchesRange = (dateFrom, dateTo, withPrediction = false) =>
  api.get(`/matches/range?date_from=${dateFrom}&date_to=${dateTo}&with_prediction=${withPrediction}`).then(r => r.data);
export const getStandings = (code) => api.get(`/standings/${code}`).then(r => r.data);
export const getCompetitionMatches = (code, status) => api.get(`/competition/${code}/matches${status ? `?status=${status}` : ""}`).then(r => r.data);
export const getCompetitionScorers = (code) => api.get(`/competition/${code}/scorers`).then(r => r.data);
export const getMatch = (id) => api.get(`/match/${id}`).then(r => r.data);
