import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
    getTournament, getPlayers, getBots, registerForTournament, registerBotForTournament,
    updateTournamentStatus, generateBracket, generateGroups, getStandings,
    advanceToPhase2, startPhase2, swapBot,
    newGame, makeMove, getAiMove, botStep, updateMatchResult, unregisterFromTournament
} from '../api'
import { HiOutlineTrophy, HiOutlineUserPlus, HiOutlineCpuChip } from 'react-icons/hi2'
import { Trash2 } from 'lucide-react'
import GameBoard from '../components/GameBoard'
import WinPredictor from '../components/WinPredictor'

export default function TournamentDetail() {
    const { id } = useParams()
    const { user } = useAuth()
    const [tournament, setTournament] = useState(null)
    const [allPlayers, setAllPlayers] = useState([])
    const [allBots, setAllBots] = useState([])
    const [showRegister, setShowRegister] = useState(false)
    const [registerType, setRegisterType] = useState('player') // 'player' or 'bot'
    const [selectedId, setSelectedId] = useState('')
    const [loading, setLoading] = useState(true)

    // In-page match play state
    const [activeMatch, setActiveMatch] = useState(null)
    const [gameState, setGameState] = useState(null)
    const [lastMove, setLastMove] = useState(null)
    const [thinking, setThinking] = useState(false)
    const [botRunning, setBotRunning] = useState(false)
    const [botDebug, setBotDebug] = useState(null)
    const stopRef = useRef(false)
    const gameRef = useRef(null)
    // Group stage state
    const [standings, setStandings] = useState(null)
    const [showSwapModal, setShowSwapModal] = useState(false)
    const [swapParticipant, setSwapParticipant] = useState('')
    const [swapNewBot, setSwapNewBot] = useState('')

    const load = () => {
        Promise.all([
            getTournament(id),
            getPlayers(),
            getBots(),
        ]).then(([tRes, pRes, bRes]) => {
            setTournament(tRes.data)
            setAllPlayers(pRes.data)
            setAllBots(bRes.data)
        }).catch(() => { })
            .finally(() => setLoading(false))
    }

    useEffect(load, [id])

    const participantName = (pid) => {
        if (!pid || pid === 'BYE') return 'BYE'
        if (pid === 'TBD') return 'TBD'
        if (pid.startsWith('bot:')) {
            const bot = allBots.find(b => b.id === pid.slice(4))
            return bot ? `🤖 ${bot.name}` : 'Unknown Bot'
        }
        const p = allPlayers.find(pl => pl.id === pid)
        return p ? p.name : 'Unknown'
    }

    const isBot = (pid) => pid && pid.startsWith('bot:')

    const handleRegister = async () => {
        if (!selectedId) return
        try {
            if (registerType === 'bot') {
                await registerBotForTournament(id, selectedId)
            } else {
                await registerForTournament(id, selectedId)
            }
            setShowRegister(false)
            setSelectedId('')
            load()
        } catch (err) {
            alert(err.response?.data?.detail || 'Registration failed')
        }
    }

    const handleUnregister = async (participantId) => {
        if (!confirm('Remove this participant from the tournament?')) return
        try {
            await unregisterFromTournament(id, participantId)
            load()
        } catch (err) {
            alert(err.response?.data?.detail || 'Unregister failed')
        }
    }

    const handleStatusChange = async (status) => {
        try {
            await updateTournamentStatus(id, status)
            load()
        } catch (err) { alert(err.response?.data?.detail || 'Update failed') }
    }

    const handleGenerateBracket = async () => {
        try {
            await generateBracket(id)
            load()
        } catch (err) { alert(err.response?.data?.detail || 'Failed to generate bracket') }
    }

    const handleGenerateGroups = async () => {
        try {
            await generateGroups(id)
            load()
            loadStandings()
        } catch (err) { alert(err.response?.data?.detail || 'Failed to generate groups') }
    }

    const loadStandings = async () => {
        try {
            const res = await getStandings(id)
            setStandings(res.data)
        } catch { }
    }

    useEffect(() => { if (tournament?.format === 'group_stage' && tournament?.phase >= 1) loadStandings() }, [tournament?.phase])

    const handleAdvancePhase2 = async () => {
        try {
            await advanceToPhase2(id)
            load()
            loadStandings()
        } catch (err) { alert(err.response?.data?.detail || 'Failed to advance') }
    }

    const handleStartPhase2 = async () => {
        try {
            await startPhase2(id)
            load()
            loadStandings()
        } catch (err) { alert(err.response?.data?.detail || 'Failed to start Phase 2') }
    }

    const handleSwapBot = async () => {
        if (!swapParticipant || !swapNewBot) return
        try {
            await swapBot(id, swapParticipant, swapNewBot)
            setShowSwapModal(false)
            setSwapParticipant('')
            setSwapNewBot('')
            load()
        } catch (err) { alert(err.response?.data?.detail || 'Swap failed') }
    }

    // --- In-page match play ---
    const startMatch = async (match) => {
        const wIsBot = isBot(match.player_white_id)
        const bIsBot = isBot(match.player_black_id)
        const mode = (wIsBot && bIsBot) ? 'bot_vs_bot' : (wIsBot || bIsBot) ? 'bot_vs_bot' : 'pvp'

        try {
            const res = await newGame({
                board_size: match.board_size,
                mode: mode,
                player_white: match.player_white_name || participantName(match.player_white_id),
                player_black: match.player_black_name || participantName(match.player_black_id),
                match_id: match.id,
                ...(wIsBot && { bot_white_id: match.player_white_id.slice(4) }),
                ...(bIsBot && { bot_black_id: match.player_black_id.slice(4) }),
            })
            setActiveMatch(match)
            setGameState(res.data)
            setLastMove(null)
            setThinking(false)
            setBotDebug(null)
            stopRef.current = false

            setTimeout(() => gameRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)

            // If both are bots, run bot loop
            if (wIsBot && bIsBot) {
                runBotLoop(res.data.game_id, match)
            }
            // If one is a bot, run human + bot alternating
            else if (wIsBot || bIsBot) {
                // If the current turn is a bot's turn, auto-play
                if ((res.data.current_player === 'W' && wIsBot) || (res.data.current_player === 'B' && bIsBot)) {
                    runSingleBotStep(res.data.game_id, match)
                }
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to start game')
        }
    }

    // Bot vs Bot: auto-play all moves
    const runBotLoop = async (gameId, match) => {
        setBotRunning(true)
        let finished = false
        while (!finished && !stopRef.current) {
            try {
                const res = await botStep(gameId)
                setGameState(res.data)
                if (res.data.bot_step_debug) setBotDebug(res.data.bot_step_debug)
                if (res.data.last_move) setLastMove({ row: res.data.last_move.row, col: res.data.last_move.col })
                if (res.data.is_finished) {
                    finished = true
                    await updateMatchResult(match.id, {
                        white_score: res.data.white_score,
                        black_score: res.data.black_score,
                        winner: res.data.winner,
                    })
                    setTimeout(() => { load(); loadStandings() }, 500)
                }
            } catch { finished = true }
        }
        setBotRunning(false)
    }

    // Single bot step (for human vs bot)
    const runSingleBotStep = async (gameId, match) => {
        setThinking(true)
        try {
            const res = await botStep(gameId)
            setGameState(res.data)
            if (res.data.bot_step_debug) setBotDebug(res.data.bot_step_debug)
            if (res.data.last_move) setLastMove({ row: res.data.last_move.row, col: res.data.last_move.col })
            if (res.data.is_finished) {
                await updateMatchResult(match.id, {
                    white_score: res.data.white_score,
                    black_score: res.data.black_score,
                    winner: res.data.winner,
                })
                setTimeout(() => { load(); loadStandings() }, 500)
            }
        } catch (err) { console.error(err) }
        setThinking(false)
    }

    const handleCellClick = useCallback(async (row, col) => {
        if (!gameState || gameState.is_finished || thinking || botRunning) return
        try {
            const res = await makeMove(gameState.game_id, row, col)
            setGameState(res.data)
            setLastMove({ row, col })

            if (res.data.is_finished) {
                await updateMatchResult(activeMatch.id, {
                    white_score: res.data.white_score,
                    black_score: res.data.black_score,
                    winner: res.data.winner,
                })
                setTimeout(() => { load(); loadStandings() }, 500)
            } else {
                // If opponent is a bot, auto-play their turn
                const wIsBot = isBot(activeMatch.player_white_id)
                const bIsBot = isBot(activeMatch.player_black_id)
                if ((res.data.current_player === 'W' && wIsBot) || (res.data.current_player === 'B' && bIsBot)) {
                    runSingleBotStep(res.data.game_id, activeMatch)
                }
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Invalid move')
        }
    }, [gameState, thinking, botRunning, activeMatch])

    const closeGame = () => {
        stopRef.current = true
        setActiveMatch(null)
        setGameState(null)
        setLastMove(null)
        setBotRunning(false)
        setBotDebug(null)
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }
    if (!tournament) {
        return <div className="text-center py-20" style={{ color: 'var(--text-secondary)' }}>Tournament not found</div>
    }

    const t = tournament
    const registeredPlayers = allPlayers.filter(p => t.registered_players.includes(p.id))
    const registeredBots = allBots.filter(b => t.registered_players.includes(`bot:${b.id}`))
    const unregisteredPlayers = allPlayers.filter(p => !t.registered_players.includes(p.id))
    const unregisteredBots = allBots.filter(b => !t.registered_players.includes(`bot:${b.id}`))
    const hasBracket = t.rounds && t.rounds.length > 0
    const statusColors = { upcoming: '#3b82f6', active: '#10b981', completed: '#64748b' }

    // Organize matches by round
    let matchesByRound = {}
    let effectiveTotalRounds = 0;

    if (hasBracket && t.matches) {
        t.matches.forEach(m => {
            const r = m.round_num || 0
            if (!matchesByRound[r]) matchesByRound[r] = []
            matchesByRound[r].push(m)
        })
        Object.values(matchesByRound).forEach(arr => arr.sort((a, b) => (a.match_index || 0) - (b.match_index || 0)))
        effectiveTotalRounds = t.total_rounds || Object.keys(matchesByRound).length
    } else if (t.status === 'upcoming' && t.format !== 'group_stage') {
        const validPids = (t.registered_players || []).filter(pid => 
            pid.startsWith('bot:') ? allBots.some(b => b.id === pid.slice(4)) : allPlayers.some(p => p.id === pid)
        );
        const pids = validPids;
        effectiveTotalRounds = Math.max(1, Math.ceil(Math.log2(Math.max(2, pids.length))));
        const previewBracketSize = Math.pow(2, effectiveTotalRounds);
        const paddedPids = [...pids, ...Array(previewBracketSize - pids.length).fill('TBD')];
        
        let currentRoundMatches = [];
        for (let i = 0; i < previewBracketSize; i += 2) {
            currentRoundMatches.push({
                id: `preview-0-${i/2}`,
                round_num: 0,
                match_index: i / 2,
                player_white_id: paddedPids[i],
                player_black_id: paddedPids[i+1],
                status: 'scheduled',
                is_preview: true
            });
        }
        matchesByRound[0] = currentRoundMatches;
        
        for (let r = 1; r < effectiveTotalRounds; r++) {
            const nextRound = [];
            for (let i = 0; i < currentRoundMatches.length; i += 2) {
                nextRound.push({
                    id: `preview-${r}-${i/2}`,
                    round_num: r,
                    match_index: i / 2,
                    player_white_id: 'TBD',
                    player_black_id: 'TBD',
                    status: 'scheduled',
                    is_preview: true
                });
            }
            matchesByRound[r] = nextRound;
            currentRoundMatches = nextRound;
        }
    }

    const totalRounds = effectiveTotalRounds;
    const roundName = (r) => {
        if (r === totalRounds - 1) return '🏆 Final'
        if (r === totalRounds - 2) return 'Semi-Final'
        if (r === totalRounds - 3) return 'Quarter-Final'
        return `Round ${r + 1}`
    }

    // Leaderboard
    const leaderboard = (() => {
        if (!t.matches) return []
        const stats = {}
        t.matches.forEach(m => {
            if (m.status !== 'completed') return
            for (const [pidKey, scoreKey, role] of [
                ['player_white_id', 'white_score', 'white'],
                ['player_black_id', 'black_score', 'black'],
            ]) {
                const pid = m[pidKey]
                if (!pid || pid === 'BYE') continue
                if (!stats[pid]) stats[pid] = { id: pid, name: participantName(pid), wins: 0, losses: 0, draws: 0, totalScore: 0, bestRound: 0 }
                stats[pid].totalScore += m[scoreKey] || 0
                stats[pid].bestRound = Math.max(stats[pid].bestRound, m.round_num || 0)
                if (m.winner === role) stats[pid].wins += 1
                else if (m.winner === 'draw') stats[pid].draws += 1
                else stats[pid].losses += 1
            }
        })
        return Object.values(stats).sort((a, b) => b.bestRound - a.bestRound || b.wins - a.wins || b.totalScore - a.totalScore)
    })()

    const coordLabel = (row, col) => {
        if (row == null || col == null) return ''
        const letter = String.fromCharCode('A'.charCodeAt(0) + row)
        return `${letter}${col + 1}`
    }

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="card p-6">
                <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className="p-3 rounded-xl" style={{ background: 'rgba(245,158,11,0.1)' }}>
                        <HiOutlineTrophy className="w-8 h-8 text-gold-500" />
                    </div>
                    <div className="flex-1">
                        <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text-primary)' }}>{t.name}</h1>
                        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{t.description || 'No description'}</p>
                        <div className="flex flex-wrap gap-3 mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                            <span>🎮 {t.board_size}×{t.board_size} Board</span>
                            <span>👥 {t.player_count}/{t.max_players} Participants</span>
                            <span>{t.format === 'group_stage' ? '🏟️ Group Stage' : '🏆 Knockout'}</span>
                            {t.format === 'group_stage' && t.phase >= 1 && (
                                <span>📍 Phase {t.phase}</span>
                            )}
                            <span className="px-2 py-0.5 rounded-full font-semibold"
                                style={{ background: statusColors[t.status] + '22', color: statusColors[t.status] }}>
                                {t.status.toUpperCase()}
                            </span>
                        </div>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {t.status === 'upcoming' && user?.role === 'ADMIN' && t.format !== 'group_stage' && (
                            <button onClick={handleGenerateBracket} className="btn-gold text-xs">🏆 Generate Bracket</button>
                        )}
                        {t.status === 'upcoming' && user?.role === 'ADMIN' && t.format === 'group_stage' && (
                            <button onClick={handleGenerateGroups} className="btn-gold text-xs">🏟️ Generate Groups</button>
                        )}
                        {t.status === 'upcoming' && (
                            <button onClick={() => { setRegisterType('player'); setSelectedId(''); setShowRegister(true) }}
                                className="btn-primary text-xs flex items-center gap-1">
                                <HiOutlineUserPlus className="w-4 h-4" /> Register
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Registered Participants (before bracket) */}
            {!hasBracket && (
                <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                            Participants ({registeredPlayers.length + registeredBots.length})
                        </h2>
                    </div>
                    {(registeredPlayers.length + registeredBots.length) > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                            {registeredPlayers.map(p => (
                                <div key={p.id} className="flex items-center gap-2 p-2 rounded-lg group" style={{ background: 'var(--bg-secondary)' }}>
                                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                                        style={{ background: p.avatar_color || '#8b5cf6' }}>{(p.name || p.username || 'U').charAt(0).toUpperCase()}</div>
                                    <span className="text-sm font-medium truncate flex-1" style={{ color: 'var(--text-primary)' }}>{p.name || p.username}</span>
                                    {t.status === 'upcoming' && (
                                        <button onClick={() => handleUnregister(p.id)} className="text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded shrink-0">
                                            <Trash2 size={14} />
                                        </button>
                                    )}
                                </div>
                            ))}
                            {registeredBots.map(b => (
                                <div key={b.id} className="flex items-center gap-2 p-2 rounded-lg group" style={{ background: 'var(--bg-secondary)' }}>
                                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0"
                                        style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: 'white' }}>🤖</div>
                                    <span className="text-sm font-medium truncate flex-1" style={{ color: 'var(--text-primary)' }}>{b.name}</span>
                                    {t.status === 'upcoming' && (
                                        <button onClick={() => handleUnregister(`bot:${b.id}`)} className="text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded shrink-0">
                                            <Trash2 size={14} />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>No participants registered yet</p>
                    )}
                </div>
            )}

            {/* ========== GROUP STAGE VIEW ========== */}
            {t.format === 'group_stage' && t.phase >= 1 && (() => {
                const groupAMatches = (t.matches || []).filter(m => m.group === 'A' && m.phase === 1)
                const groupBMatches = (t.matches || []).filter(m => m.group === 'B' && m.phase === 1)
                const phase2Matches = (t.matches || []).filter(m => m.phase === 2)
                const allP1Done = [...groupAMatches, ...groupBMatches].length > 0 && [...groupAMatches, ...groupBMatches].every(m => m.status === 'completed')
                const allP2Done = phase2Matches.length > 0 && phase2Matches.every(m => m.status === 'completed')

                const StandingsTable = ({ rows, title, showQualify }) => (
                    <div className="card p-4">
                        <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>{title}</h3>
                        <table className="w-full text-xs">
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    {['#', 'Team', 'P', 'W', 'D', 'L', 'PF', 'PA', 'Pts'].map(h => (
                                        <th key={h} className={`py-1.5 px-1 ${h === 'Team' ? 'text-left' : 'text-center'} font-semibold`}
                                            style={{ color: 'var(--text-muted)' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {(rows || []).map((s, i) => (
                                    <tr key={s.id} style={{
                                        borderBottom: '1px solid var(--border-color)',
                                        background: showQualify && i < 4 ? 'rgba(16,185,129,0.06)' : undefined,
                                    }}>
                                        <td className="py-1.5 px-1 text-center font-bold" style={{ color: i === 0 ? '#f59e0b' : 'var(--text-muted)' }}>
                                            {i === 0 ? '🥇' : i + 1}
                                        </td>
                                        <td className="py-1.5 px-1 font-semibold truncate max-w-[120px]" style={{ color: 'var(--text-primary)' }}>{s.name}</td>
                                        <td className="py-1.5 px-1 text-center" style={{ color: 'var(--text-secondary)' }}>{s.played}</td>
                                        <td className="py-1.5 px-1 text-center font-bold" style={{ color: '#10b981' }}>{s.wins}</td>
                                        <td className="py-1.5 px-1 text-center" style={{ color: '#f59e0b' }}>{s.draws}</td>
                                        <td className="py-1.5 px-1 text-center" style={{ color: '#ef4444' }}>{s.losses}</td>
                                        <td className="py-1.5 px-1 text-center" style={{ color: 'var(--text-secondary)' }}>{s.score_for}</td>
                                        <td className="py-1.5 px-1 text-center" style={{ color: 'var(--text-secondary)' }}>{s.score_against}</td>
                                        <td className="py-1.5 px-1 text-center font-extrabold" style={{ color: '#3b82f6' }}>{s.points}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {showQualify && <p className="text-[10px] mt-2" style={{ color: '#10b981' }}>✅ Top 4 qualify for Phase 2</p>}
                    </div>
                )

                const MatchCard = ({ m }) => {
                    const isDone = m.status === 'completed'
                    const wName = m.player_white_name || participantName(m.player_white_id)
                    const bName = m.player_black_name || participantName(m.player_black_id)
                    return (
                        <div className="flex items-center gap-2 p-2 rounded-lg text-xs" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                            <div className="flex-1 truncate font-semibold" style={{ color: isDone && m.winner === 'white' ? '#10b981' : 'var(--text-primary)' }}>{wName}</div>
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full font-bold" style={{ background: 'var(--bg-card)' }}>
                                <span style={{ color: isDone && m.winner === 'white' ? '#10b981' : 'var(--text-primary)' }}>{isDone ? m.white_score : '-'}</span>
                                <span style={{ color: 'var(--text-muted)' }}>:</span>
                                <span style={{ color: isDone && m.winner === 'black' ? '#10b981' : 'var(--text-primary)' }}>{isDone ? m.black_score : '-'}</span>
                            </div>
                            <div className="flex-1 truncate text-right font-semibold" style={{ color: isDone && m.winner === 'black' ? '#10b981' : 'var(--text-primary)' }}>{bName}</div>
                            {!isDone && m.status === 'scheduled' && !activeMatch && (
                                <button onClick={() => startMatch(m)} className="ml-1 px-2 py-0.5 rounded text-[10px] font-bold text-white"
                                    style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)' }}>▶</button>
                            )}
                        </div>
                    )
                }

                return (
                    <>
                        {/* Phase 1: Group Tables */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <StandingsTable rows={standings?.group_a} title="🅰️ Group A" showQualify={allP1Done && t.phase === 1} />
                            <StandingsTable rows={standings?.group_b} title="🅱️ Group B" showQualify={allP1Done && t.phase === 1} />
                        </div>

                        {/* Phase 1 Matches */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="card p-4">
                                <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Group A Matches ({groupAMatches.filter(m => m.status === 'completed').length}/{groupAMatches.length})</h3>
                                <div className="space-y-2">
                                    {groupAMatches.map(m => <MatchCard key={m.id} m={m} />)}
                                    {groupAMatches.length === 0 && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No matches yet</p>}
                                </div>
                            </div>
                            <div className="card p-4">
                                <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Group B Matches ({groupBMatches.filter(m => m.status === 'completed').length}/{groupBMatches.length})</h3>
                                <div className="space-y-2">
                                    {groupBMatches.map(m => <MatchCard key={m.id} m={m} />)}
                                    {groupBMatches.length === 0 && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No matches yet</p>}
                                </div>
                            </div>
                        </div>

                        {/* Phase 1 → Phase 2 transition */}
                        {allP1Done && t.phase === 1 && (
                            <div className="card p-6 text-center">
                                <h2 className="text-lg font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>✅ Phase 1 Complete!</h2>
                                <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>Top 4 from each group will advance to the Finals round-robin.</p>
                                <button onClick={handleAdvancePhase2} className="btn-gold">🚀 Advance Top Teams to Phase 2</button>
                            </div>
                        )}

                        {/* Swap Window */}
                        {t.phase === 2 && t.phase2_status === 'swap_window' && (
                            <div className="card p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h2 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>🔄 Bot Swap Window</h2>
                                        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Teams can change their bot before Phase 2 begins</p>
                                    </div>
                                    <button onClick={handleStartPhase2} className="btn-gold text-xs">⚡ Close Window & Start Phase 2</button>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                    {(t.phase2_participants || []).map(pid => (
                                        <div key={pid} className="flex items-center gap-2 p-2 rounded-lg" style={{ background: 'var(--bg-secondary)' }}>
                                            <span className="text-xs font-semibold flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{participantName(pid)}</span>
                                            <button onClick={() => { setSwapParticipant(pid); setSwapNewBot(''); setShowSwapModal(true) }}
                                                className="text-[10px] px-2 py-0.5 rounded font-bold"
                                                style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }}>Swap</button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Phase 2: Finals */}
                        {t.phase >= 2 && t.phase2_status !== 'swap_window' && (
                            <>
                                <StandingsTable rows={standings?.phase2} title="🏆 Phase 2 — Finals Standings" />
                                <div className="card p-4">
                                    <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Finals Matches ({phase2Matches.filter(m => m.status === 'completed').length}/{phase2Matches.length})</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                        {phase2Matches.map(m => <MatchCard key={m.id} m={m} />)}
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Tournament Winner */}
                        {allP2Done && standings?.phase2?.[0] && (
                            <div className="card p-6 text-center" style={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02))' }}>
                                <div className="text-4xl mb-2">🏆</div>
                                <h2 className="text-xl font-extrabold" style={{ color: '#f59e0b' }}>Winner: {standings.phase2[0].name}</h2>
                                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                                    {standings.phase2[0].wins}W {standings.phase2[0].draws}D {standings.phase2[0].losses}L — {standings.phase2[0].points} points
                                </p>
                            </div>
                        )}

                        {/* Swap Bot Modal */}
                        {showSwapModal && (
                            <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowSwapModal(false)}>
                                <div className="card p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
                                    <h2 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>🔄 Swap Bot</h2>
                                    <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>Swapping for: <strong>{participantName(swapParticipant)}</strong></p>
                                    <select className="glass-input w-full bg-black/40 text-white border-white/10 mb-3" value={swapNewBot} onChange={e => setSwapNewBot(e.target.value)}>
                                        <option value="" className="bg-black text-slate-400">Select new bot…</option>
                                        {allBots.map(b => <option key={b.id} value={b.id} className="bg-black text-white">{b.name} {b.owner ? `(${b.owner})` : ''}</option>)}
                                    </select>
                                    <div className="flex gap-2">
                                        <button onClick={() => setShowSwapModal(false)} className="btn-secondary flex-1">Cancel</button>
                                        <button onClick={handleSwapBot} className="btn-primary flex-1" disabled={!swapNewBot}>Swap</button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )
            })()}

            {/* In-Page Match Play */}
            {activeMatch && gameState && (
                <div ref={gameRef} className="card p-6" style={{ borderColor: '#f59e0b', borderWidth: '2px' }}>
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h2 className="text-lg font-extrabold" style={{ color: 'var(--text-primary)' }}>
                                {gameState.is_finished ? '🏆 Match Complete!' : botRunning ? '⚔️ Bots Playing Live...' : '🎮 Match In Progress'}
                            </h2>
                            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                {roundName(activeMatch.round_num)} • {gameState.board_size}×{gameState.board_size} • Turn {gameState.turn}
                            </p>
                        </div>
                        <button onClick={closeGame} className="btn-secondary text-xs">
                            {gameState.is_finished ? 'Close' : 'Abort'}
                        </button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-6">
                        <div className="flex flex-col items-center justify-center">
                            <WinPredictor gameState={gameState} />
                            <GameBoard
                                board={gameState.board}
                                boardSize={gameState.board_size}
                                currentPlayer={gameState.current_player}
                                onCellClick={handleCellClick}
                                disabled={gameState.is_finished || thinking || botRunning}
                                lastMove={lastMove}
                            />
                        </div>

                        <div className="space-y-3">
                            {[
                                { name: gameState.player_white, score: gameState.white_score, color: 'W', isActive: gameState.current_player === 'W' && !gameState.is_finished },
                                { name: gameState.player_black, score: gameState.black_score, color: 'B', isActive: gameState.current_player === 'B' && !gameState.is_finished },
                            ].map(({ name, score, color, isActive }) => (
                                <div key={color} className="p-3 rounded-lg transition-all duration-300" style={{
                                    background: 'var(--bg-secondary)',
                                    borderLeft: isActive ? `3px solid ${color === 'W' ? '#e2e8f0' : '#334155'}` : '3px solid transparent',
                                }}>
                                    <div className="flex items-center gap-2">
                                        <div className={`w-6 h-6 rounded-full ${color === 'W' ? 'bg-white border-2 border-slate-300' : 'bg-red-600 border-2 border-red-400'}`} />
                                        <span className="text-sm font-semibold flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{name}</span>
                                        <span className="text-xl font-extrabold" style={{ color: 'var(--text-primary)' }}>{score}</span>
                                    </div>
                                    {isActive && !botRunning && !thinking && <p className="text-[10px] mt-1 ml-8" style={{ color: '#f59e0b' }}>Your turn — click the board</p>}
                                    {isActive && (botRunning || thinking) && <p className="text-[10px] mt-1 ml-8" style={{ color: '#3b82f6' }}>Thinking...</p>}
                                </div>
                            ))}

                            <div className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)' }}>
                                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
                                    <div className="h-full rounded-full transition-all duration-500" style={{
                                        width: `${gameState.total_cells > 0 ? (gameState.cells_filled / gameState.total_cells) * 100 : 0}%`,
                                        background: 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                                    }} />
                                </div>
                                <p className="text-[10px] mt-1 text-center" style={{ color: 'var(--text-muted)' }}>
                                    {gameState.cells_filled}/{gameState.total_cells} cells
                                </p>
                            </div>

                            {/* Live Logs for tournament matches */}
                            {botDebug && (
                                <div className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)' }}>
                                    <p className="text-[11px] font-bold mb-1" style={{ color: 'var(--text-muted)' }}>
                                        LIVE LOGS
                                    </p>
                                    {botDebug.forfeited && (
                                        <p className="text-[11px] mb-1" style={{ color: '#ef4444' }}>
                                            Current bot forfeited after {botDebug.max_attempts} failed attempts. Opponent wins.
                                        </p>
                                    )}
                                    {botDebug.attempts && botDebug.attempts.length > 0 ? (
                                        botDebug.attempts.slice(-3).map((a) => (
                                            <div key={a.attempt} className="text-[10px] py-0.5">
                                                <span className="font-mono mr-1" style={{ color: 'var(--text-muted)' }}>
                                                    #{a.attempt}
                                                </span>
                                                <span className="font-semibold mr-1" style={{ color: a.source === 'bot' ? '#f59e0b' : '#3b82f6' }}>
                                                    {a.source === 'bot' ? 'BOT' : 'API'}
                                                </span>
                                                {a.error_type ? (
                                                    <span style={{ color: 'var(--text-secondary)' }}>
                                                        {a.error_type} — {a.message}
                                                    </span>
                                                ) : a.success ? (
                                                    <span style={{ color: '#10b981' }}>
                                                        success → {coordLabel(a.move?.row, a.move?.col)}
                                                    </span>
                                                ) : null}
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                            No bot-step debug info yet.
                                        </p>
                                    )}
                                </div>
                            )}

                            {gameState.is_finished && (
                                <div className="p-4 rounded-lg text-center" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.1))' }}>
                                    <p className="text-lg font-black" style={{ color: 'var(--text-primary)' }}>
                                        {gameState.winner === 'draw' ? '🤝 Draw!' :
                                            `🏆 ${gameState.winner === 'white' ? gameState.player_white : gameState.player_black} Wins!`}
                                    </p>
                                    <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{gameState.white_score} - {gameState.black_score}</p>
                                    <p className="text-[10px] mt-2" style={{ color: '#10b981' }}>✓ Result saved and bracket updated</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Knockout Bracket */}
            {(hasBracket || (t.status === 'upcoming' && t.format !== 'group_stage')) && (
                <div className="card p-6">
                    <h2 className="text-base font-bold mb-4" style={{ color: 'var(--text-primary)' }}>🏆 Knockout Bracket {!hasBracket && <span className="text-sm font-normal text-amber-500 ml-2">(Live Preview)</span>}</h2>
                    <div className="overflow-x-auto">
                        <div className="flex gap-8 min-w-max py-2">
                            {Array.from({ length: totalRounds }, (_, r) => {
                                const matches = matchesByRound[r] || []
                                return (
                                    <div key={r} className="flex flex-col gap-2" style={{ minWidth: '200px' }}>
                                        <h3 className="text-xs font-bold text-center mb-2 px-3 py-1.5 rounded-full"
                                            style={{
                                                background: r === totalRounds - 1 ? 'rgba(245,158,11,0.15)' : 'var(--bg-secondary)',
                                                color: r === totalRounds - 1 ? '#f59e0b' : 'var(--text-muted)',
                                            }}>
                                            {roundName(r)}
                                        </h3>
                                        <div className="flex flex-col justify-around flex-1 gap-3">
                                            {matches.map(m => {
                                                const isDone = m.status === 'completed'
                                                const isBye = m.player_black_id === 'BYE'
                                                const canPlay = m.status === 'scheduled' && !activeMatch && !m.is_preview
                                                
                                                const wName = m.player_white_name || participantName(m.player_white_id)
                                                const bName = isBye ? 'BYE' : (m.player_black_name || participantName(m.player_black_id))

                                                return (
                                                    <div key={m.id} className={`rounded-xl border transition-all duration-200 overflow-hidden relative ${isDone ? 'opacity-90' : ''}`}
                                                        style={{
                                                            borderColor: isDone ? '#10b98133' : canPlay ? '#3b82f6' : m.is_preview ? 'rgba(255,255,255,0.05)' : 'var(--border-color)',
                                                            background: isDone ? 'var(--bg-secondary)' : 'var(--bg-primary)',
                                                            boxShadow: canPlay ? '0 0 10px rgba(59,130,246,0.3)' : 'none',
                                                        }}>
                                                        {/* Play Button Overlay for Admins */}
                                                        {canPlay && user?.role === 'ADMIN' && (
                                                            <div className="absolute inset-y-0 right-0 flex items-center pr-2">
                                                                <button onClick={() => startMatch(m)} className="px-2 py-1 rounded text-xs font-bold text-white shadow-lg z-10 hover:scale-105 transition-transform"
                                                                    style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)' }}>▶ Play</button>
                                                            </div>
                                                        )}
                                                        {/* White */}
                                                        <div className="flex items-center gap-2 px-3 py-2 border-b"
                                                            style={{
                                                                borderColor: 'var(--border-color)',
                                                                background: isDone && m.winner === 'white' ? 'rgba(16,185,129,0.05)' : undefined,
                                                            }}>
                                                            <div className="w-3 h-3 rounded-full bg-white border border-slate-300 shrink-0" />
                                                            <span className={`text-xs font-semibold flex-1 truncate ${isDone && m.winner !== 'white' && m.winner !== 'draw' ? 'line-through opacity-40' : ''}`}
                                                                style={{ color: isDone && m.winner === 'white' ? '#10b981' : 'var(--text-primary)' }}>
                                                                {wName}
                                                            </span>
                                                            <span className="text-xs font-extrabold w-6 text-right" style={{ color: isDone && m.winner === 'white' ? '#10b981' : 'var(--text-muted)' }}>{isDone ? m.white_score : '-'}</span>
                                                        </div>
                                                        {/* Black */}
                                                        <div className="flex items-center gap-2 px-3 py-2"
                                                            style={{ background: isDone && m.winner === 'black' ? 'rgba(16,185,129,0.05)' : undefined }}>
                                                            <div className="w-3 h-3 rounded-full bg-red-600 border border-red-400 shrink-0" />
                                                            <span className={`text-xs font-semibold flex-1 truncate ${isDone && m.winner !== 'black' && m.winner !== 'draw' ? 'line-through opacity-40' : ''} ${isBye ? 'italic opacity-40' : ''}`}
                                                                style={{ color: isDone && m.winner === 'black' ? '#10b981' : 'var(--text-primary)' }}>
                                                                {bName}
                                                            </span>
                                                            {!isBye && <span className="text-xs font-extrabold w-6 text-right" style={{ color: isDone && m.winner === 'black' ? '#10b981' : 'var(--text-muted)' }}>{isDone ? m.black_score : '-'}</span>}
                                                        </div>
                                                        {isDone && !isBye && (
                                                            <div className="text-center py-1 text-[10px] font-semibold" style={{ color: '#10b981' }}>✓ Complete</div>
                                                        )}
                                                        {isBye && isDone && (
                                                            <div className="text-center py-1 text-[10px] italic" style={{ color: 'var(--text-muted)' }}>auto-advance</div>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                            {matches.length === 0 && (
                                                <div className="text-center py-8 text-xs" style={{ color: 'var(--text-muted)' }}>
                                                    Waiting for previous round...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Tournament Leaderboard */}
            {hasBracket && leaderboard.length > 0 && (
                <div className="card p-6">
                    <h2 className="text-base font-bold mb-4" style={{ color: 'var(--text-primary)' }}>📊 Tournament Leaderboard</h2>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    {['#', 'Participant', 'Round', 'W', 'L', 'Score'].map(h => (
                                        <th key={h} className={`${h === '#' || h === 'Participant' ? 'text-left' : 'text-center'} py-2 px-3 text-xs font-semibold`}
                                            style={{ color: 'var(--text-muted)' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {leaderboard.map((p, i) => (
                                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                        <td className="py-2.5 px-3">
                                            <span className="text-xs font-bold" style={{ color: i === 0 ? '#f59e0b' : i === 1 ? '#94a3b8' : i === 2 ? '#cd7f32' : 'var(--text-muted)' }}>
                                                {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}
                                            </span>
                                        </td>
                                        <td className="py-2.5 px-3">
                                            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{p.name}</span>
                                        </td>
                                        <td className="text-center py-2.5 px-3">
                                            <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
                                                style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                                                {roundName(p.bestRound)}
                                            </span>
                                        </td>
                                        <td className="text-center py-2.5 px-3 text-xs font-bold" style={{ color: '#10b981' }}>{p.wins}</td>
                                        <td className="text-center py-2.5 px-3 text-xs font-bold" style={{ color: '#ef4444' }}>{p.losses}</td>
                                        <td className="text-center py-2.5 px-3 text-xs font-bold" style={{ color: '#3b82f6' }}>{p.totalScore}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Register Modal */}
            {showRegister && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowRegister(false)}>
                    <div className="card p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
                        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Register Participant</h2>

                        {/* Type toggle */}
                        <div className="flex gap-2 mb-4">
                            <button onClick={() => { setRegisterType('player'); setSelectedId('') }}
                                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${registerType === 'player' ? 'text-white' : ''}`}
                                style={{
                                    background: registerType === 'player' ? 'linear-gradient(135deg, #3b82f6, #4f46e5)' : 'var(--bg-secondary)',
                                    color: registerType === 'player' ? 'white' : 'var(--text-secondary)',
                                }}>
                                👤 Player
                            </button>
                            <button onClick={() => { setRegisterType('bot'); setSelectedId('') }}
                                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all`}
                                style={{
                                    background: registerType === 'bot' ? 'linear-gradient(135deg, #60a5fa, #3b82f6)' : 'var(--bg-secondary)',
                                    color: registerType === 'bot' ? 'white' : 'var(--text-secondary)',
                                }}>
                                🤖 Bot
                            </button>
                        </div>

                        {registerType === 'player' ? (
                            unregisteredPlayers.length === 0 ? (
                                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>All players are already registered!</p>
                            ) : (
                                <div className="space-y-3">
                                    <select className="glass-input w-full bg-black/40 text-white border-white/10" value={selectedId} onChange={e => setSelectedId(e.target.value)}>
                                        <option value="" className="bg-black text-slate-400">Select a player</option>
                                        {unregisteredPlayers.map(p => (<option key={p.id} value={p.id} className="bg-black text-white">{p.name}</option>))}
                                    </select>
                                    <div className="flex gap-2">
                                        <button onClick={() => setShowRegister(false)} className="btn-secondary flex-1">Cancel</button>
                                        <button onClick={handleRegister} className="btn-primary flex-1" disabled={!selectedId}>Register</button>
                                    </div>
                                </div>
                            )
                        ) : (
                            unregisteredBots.length === 0 ? (
                                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                    {allBots.length === 0 ? 'No bots available. Register bots on the Bots page first!' : 'All bots are already registered!'}
                                </p>
                            ) : (
                                <div className="space-y-3">
                                    <select className="glass-input w-full bg-black/40 text-white border-white/10" value={selectedId} onChange={e => setSelectedId(e.target.value)}>
                                        <option value="" className="bg-black text-slate-400">Select a bot</option>
                                        {unregisteredBots.map(b => (<option key={b.id} value={b.id} className="bg-black text-white">{b.name} {b.owner ? `(${b.owner})` : ''}</option>))}
                                    </select>
                                    <div className="flex gap-2">
                                        <button onClick={() => setShowRegister(false)} className="btn-secondary flex-1">Cancel</button>
                                        <button onClick={handleRegister} className="btn-primary flex-1" disabled={!selectedId}>Register</button>
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
