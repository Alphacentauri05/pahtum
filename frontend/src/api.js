import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    timeout: 10000,
})

// Request Interceptor: Attach token to headers
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => Promise.reject(error));

// Response Interceptor: Handle 401 Unauthorized
api.interceptors.response.use((response) => response, (error) => {
    if (error.response && error.response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
    return Promise.reject(error);
});

// ---- Players ----
export const createPlayer = (data) => api.post('/players', data)
export const getPlayers = () => api.get('/players')
export const getPlayer = (id) => api.get(`/players/${id}`)
export const updatePlayer = (id, data) => api.put(`/players/${id}`, data)
export const deletePlayer = (id) => api.delete(`/players/${id}`)

// ---- Tournaments ----
export const createTournament = (data) => api.post('/tournaments', data)
export const getTournaments = () => api.get('/tournaments')
export const getTournament = (id) => api.get(`/tournaments/${id}`)
export const updateTournamentStatus = (id, status) =>
    api.put(`/tournaments/${id}?status=${status}`)
export const editTournament = (id, data) => api.put(`/tournaments/${id}/edit`, data)
export const deleteTournament = (id) => api.delete(`/tournaments/${id}`)
export const registerForTournament = (tid, playerId) =>
    api.post(`/tournaments/${tid}/register?player_id=${playerId}`)
export const registerBotForTournament = (tid, botId) =>
    api.post(`/tournaments/${tid}/register-bot?bot_id=${botId}`)
export const unregisterFromTournament = (tid, participantId) =>
    api.post(`/tournaments/${tid}/unregister?participant_id=${participantId}`)
export const generateBracket = (tid) =>
    api.post(`/tournaments/${tid}/generate-bracket`)
// Group Stage
export const generateGroups = (tid) =>
    api.post(`/tournaments/${tid}/generate-groups`)
export const getStandings = (tid) =>
    api.get(`/tournaments/${tid}/standings`)
export const advanceToPhase2 = (tid) =>
    api.post(`/tournaments/${tid}/advance-to-phase2`)
export const startPhase2 = (tid) =>
    api.post(`/tournaments/${tid}/start-phase2`)
export const swapBot = (tid, participantId, newBotId) =>
    api.post(`/tournaments/${tid}/swap-bot?participant_id=${participantId}&new_bot_id=${newBotId}`)

// ---- Matches ----
export const createMatch = (data) => api.post('/matches', data)
export const getMatches = (tournamentId) =>
    api.get('/matches', { params: tournamentId ? { tournament_id: tournamentId } : {} })
export const getMatch = (id) => api.get(`/matches/${id}`)
export const updateMatchResult = (mid, data) =>
    api.put(`/matches/${mid}/result`, null, { params: data })

// ---- Game ----
export const newGame = (data) => api.post('/game/new', data)
export const makeMove = (gameId, row, col) =>
    api.post(`/game/${gameId}/move`, { row, col })
export const getAiMove = (gameId) => api.post(`/game/${gameId}/ai-move`)
export const botStep = (gameId) => api.post(`/game/${gameId}/bot-step`, null, { timeout: 15000 })
export const getGameState = (gameId) => api.get(`/game/${gameId}`)

// ---- Leaderboard & Stats ----
export const getLeaderboard = () => api.get('/leaderboard')
export const getOverviewStats = () => api.get('/stats/overview')

// ---- Bots ----
export const createBot = (data) => api.post('/bots', data)
export const getBots = () => api.get('/bots')
export const getBot = (id) => api.get(`/bots/${id}`)
export const updateBot = (id, data) => api.put(`/bots/${id}`, data)
export const testBot = (id) => api.post(`/bots/${id}/test`)
export const deleteBot = (id) => api.delete(`/bots/${id}`)
export const uploadLocalBot = (formData) =>
    api.post('/bots/upload-local', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
export const createInlineBot = (data) => api.post('/bots/inline', data)
export const runBotGame = (params) =>
    api.post('/game/bot-game/run', null, { params, timeout: 60000 })

export default api
