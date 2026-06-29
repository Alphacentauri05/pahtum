import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { newGame, makeMove, getAiMove, getPlayers, getBots, botStep } from '../api'
import GameBoard from '../components/GameBoard'
import WinPredictor from '../components/WinPredictor'

export default function PlayGame() {
    const [searchParams] = useSearchParams()
    const [gameState, setGameState] = useState(null)
    const [setup, setSetup] = useState({
        board_size: parseInt(searchParams.get('board')) || 7,
        mode: 'vs_ai',
        player_white: 'Player 1',
        player_black: 'AI Bot',
    })
    const [players, setPlayers] = useState([])
    const [bots, setBots] = useState([])
    const [botWhiteId, setBotWhiteId] = useState('')
    const [botBlackId, setBotBlackId] = useState('')
    const [started, setStarted] = useState(false)
    const [thinking, setThinking] = useState(false)
    const [lastMove, setLastMove] = useState(null)

    // Bot vs Bot live state
    const [moveLog, setMoveLog] = useState([])
    const [botRunning, setBotRunning] = useState(false)
    const [botDebug, setBotDebug] = useState(null)
    const stopRef = useRef(false)
    const logEndRef = useRef(null)

    useEffect(() => {
        getPlayers().then(res => setPlayers(res.data)).catch(() => { })
        getBots().then(res => setBots(res.data)).catch(() => { })
    }, [])

    // Auto-scroll move log
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [moveLog])

    const startGame = async () => {
        if (setup.mode === 'bot_vs_bot') {
            if (!botWhiteId || !botBlackId) return alert('Select both bots')
            if (botWhiteId === botBlackId) return alert('Select two different bots')

            // Create a normal game with bot_vs_bot mode
            try {
                const res = await newGame({
                    board_size: setup.board_size,
                    mode: 'bot_vs_bot',
                    player_white: bots.find(b => b.id === botWhiteId)?.name || 'Bot A',
                    player_black: bots.find(b => b.id === botBlackId)?.name || 'Bot B',
                    bot_white_id: botWhiteId,
                    bot_black_id: botBlackId,
                })
                setGameState(res.data)
                setStarted(true)
                setMoveLog([])
                setLastMove(null)
                stopRef.current = false
                // Start the live bot loop
                runBotLoop(res.data.game_id)
            } catch (err) {
                alert(err.response?.data?.detail || 'Failed to start game')
            }
            return
        }

        try {
            const res = await newGame({
                board_size: setup.board_size,
                mode: setup.mode,
                player_white: setup.player_white,
                player_black: setup.player_black,
                match_id: searchParams.get('match') || null,
            })
            setGameState(res.data)
            setStarted(true)
            setLastMove(null)
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to start game')
        }
    }

    // Live bot-vs-bot loop: calls /bot-step one at a time
    const runBotLoop = async (gameId) => {
        setBotRunning(true)
        let finished = false

        while (!finished && !stopRef.current) {
            try {
                const res = await botStep(gameId)
                const state = res.data
                setGameState(state)
                if (state.bot_step_debug) {
                    setBotDebug(state.bot_step_debug)
                }

                if (state.last_move) {
                    setLastMove({ row: state.last_move.row, col: state.last_move.col })
                    setMoveLog(prev => [...prev, state.last_move])
                }

                if (state.is_finished) {
                    finished = true
                }
            } catch (err) {
                console.error('Bot step failed:', err)
                finished = true
            }
        }
        setBotRunning(false)
    }

    const handleCellClick = useCallback(async (row, col) => {
        if (!gameState || gameState.is_finished || thinking) return

        try {
            const res = await makeMove(gameState.game_id, row, col)
            setGameState(res.data)
            setLastMove({ row, col })

            if (setup.mode === 'vs_ai' && !res.data.is_finished) {
                setThinking(true)
                setTimeout(async () => {
                    try {
                        const aiRes = await getAiMove(res.data.game_id)
                        setGameState(aiRes.data)
                        const aiMoveData = aiRes.data.moves[aiRes.data.moves.length - 1]
                        if (aiMoveData) setLastMove({ row: aiMoveData.row, col: aiMoveData.col })
                    } catch (err) {
                        console.error('AI move failed:', err)
                    } finally {
                        setThinking(false)
                    }
                }, 500)
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Invalid move')
        }
    }, [gameState, thinking, setup.mode])

    const resetGame = () => {
        stopRef.current = true
        setGameState(null)
        setStarted(false)
        setLastMove(null)
        setThinking(false)
        setMoveLog([])
        setBotRunning(false)
        setBotDebug(null)
    }

    // ===== SETUP SCREEN =====
    if (!started) {
        return (
            <div className="max-w-2xl mx-auto space-y-6">
                <div>
                    <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Play Pah-Tum</h1>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Set up your game and start playing</p>
                </div>

                <div className="card p-6 space-y-5">
                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Game Mode</label>
                        <div className="grid grid-cols-3 gap-3">
                            {[
                                { id: 'vs_ai', label: '🤖 vs AI', desc: 'Play against computer' },
                                { id: 'pvp', label: '👥 PvP', desc: 'Two players locally' },
                                { id: 'bot_vs_bot', label: '⚔️ Bot vs Bot', desc: 'API bots compete' },
                            ].map(m => (
                                <button
                                    key={m.id}
                                    onClick={() => setSetup(s => ({
                                        ...s,
                                        mode: m.id,
                                        player_black: m.id === 'vs_ai' ? 'AI Bot' : m.id === 'bot_vs_bot' ? 'Bot B' : 'Player 2',
                                        player_white: m.id === 'bot_vs_bot' ? 'Bot A' : 'Player 1',
                                    }))}
                                    className={`p-4 rounded-xl text-left transition-all duration-200 border ${setup.mode === m.id
                                        ? 'border-primary-500 bg-primary-500/10'
                                        : ''
                                        }`}
                                    style={{
                                        background: setup.mode === m.id ? undefined : 'var(--bg-secondary)',
                                        borderColor: setup.mode === m.id ? undefined : 'var(--border-color)',
                                    }}
                                >
                                    <div className="text-lg mb-1">{m.label}</div>
                                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{m.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Board Size</label>
                        <div className="flex flex-wrap gap-2">
                            {[3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                                <button
                                    key={n}
                                    onClick={() => setSetup(s => ({ ...s, board_size: n }))}
                                    className={`w-12 h-12 rounded-lg font-bold text-sm transition-all duration-200`}
                                    style={{
                                        background: setup.board_size === n ? 'linear-gradient(135deg, #3b82f6, #4f46e5)' : 'var(--bg-secondary)',
                                        color: setup.board_size === n ? 'white' : 'var(--text-primary)',
                                        border: `1px solid ${setup.board_size === n ? '#3b82f6' : 'var(--border-color)'}`,
                                    }}
                                >
                                    {n}
                                </button>
                            ))}
                        </div>
                        <p className="mt-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>{setup.board_size}×{setup.board_size} = {setup.board_size * setup.board_size} cells</p>
                    </div>

                    {/* Bot selectors for bot_vs_bot mode */}
                    {setup.mode === 'bot_vs_bot' ? (
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>⬜ White Bot</label>
                                <select
                                    className="input-field"
                                    value={botWhiteId}
                                    onChange={e => setBotWhiteId(e.target.value)}
                                >
                                    <option value="">Select a bot...</option>
                                    {bots.map(b => (
                                        <option key={b.id} value={b.id}>{b.name} {b.owner ? `(${b.owner})` : ''}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>⬛ Black Bot</label>
                                <select
                                    className="input-field"
                                    value={botBlackId}
                                    onChange={e => setBotBlackId(e.target.value)}
                                >
                                    <option value="">Select a bot...</option>
                                    {bots.map(b => (
                                        <option key={b.id} value={b.id}>{b.name} {b.owner ? `(${b.owner})` : ''}</option>
                                    ))}
                                </select>
                            </div>
                            {bots.length === 0 && (
                                <p className="col-span-2 text-xs text-center py-2" style={{ color: '#f59e0b' }}>
                                    No bots registered yet. Go to the Bots page to add some!
                                </p>
                            )}
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>White (First)</label>
                                <input
                                    className="input-field"
                                    value={setup.player_white}
                                    onChange={e => setSetup(s => ({ ...s, player_white: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Black (Second)</label>
                                <input
                                    className="input-field"
                                    value={setup.player_black}
                                    onChange={e => setSetup(s => ({ ...s, player_black: e.target.value }))}
                                    disabled={setup.mode === 'vs_ai'}
                                    style={{ opacity: setup.mode === 'vs_ai' ? 0.5 : 1 }}
                                />
                            </div>
                        </div>
                    )}

                    <button onClick={startGame} className="btn-gold w-full text-base py-3">
                        {setup.mode === 'bot_vs_bot' ? '⚔️ Run Bot Battle' : '🎮 Start Game'}
                    </button>
                </div>

                {/* Scoring Table Preview */}
                <div className="card p-6">
                    <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>📊 Scoring Table (Board {setup.board_size}×{setup.board_size})</h3>
                    <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
                        {Array.from({ length: setup.board_size }, (_, i) => i + 1).map(L => {
                            let pts = 0
                            if (L >= 3) {
                                pts = 3
                                for (let k = 4; k <= L; k++) pts = 2 * pts + k
                            }
                            return (
                                <div key={L} className="text-center p-2 rounded-lg" style={{ background: 'var(--bg-secondary)' }}>
                                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Run {L}</div>
                                    <div className="text-sm font-bold" style={{ color: pts > 0 ? '#10b981' : 'var(--text-muted)' }}>
                                        {pts > 0 ? pts : '—'}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </div>
        )
    }

    // ===== GAME IN PROGRESS (all modes) =====
    const gs = gameState
    const progress = gs ? Math.round((gs.cells_filled / gs.total_cells) * 100) : 0
    const isBotGame = setup.mode === 'bot_vs_bot'

    const coordLabel = (row, col) => {
        if (row == null || col == null) return ''
        const letter = String.fromCharCode('A'.charCodeAt(0) + row)
        return `${letter}${col + 1}`
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            {/* Game Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl md:text-2xl font-extrabold" style={{ color: 'var(--text-primary)' }}>
                        {gs?.is_finished ? '🏆 Game Over!' :
                            isBotGame ? (botRunning ? '⚔️ Bots Playing Live...' : '⚔️ Bot Battle') :
                                '🎮 Game In Progress'}
                    </h1>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {setup.board_size}×{setup.board_size} •
                        {isBotGame ? ' Bot vs Bot' : setup.mode === 'vs_ai' ? ' vs AI' : ' PvP'} •
                        Turn {gs?.turn || 0}
                    </p>
                </div>
                <button onClick={resetGame} className="btn-secondary text-xs">New Game</button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
                {/* Board */}
                <div className="card p-6 flex flex-col items-center justify-center">
                    <WinPredictor gameState={gs} />
                    <GameBoard
                        board={gs?.board}
                        boardSize={gs?.board_size || setup.board_size}
                        currentPlayer={gs?.current_player}
                        onCellClick={isBotGame ? () => { } : handleCellClick}
                        disabled={gs?.is_finished || thinking || isBotGame}
                        lastMove={lastMove}
                    />
                </div>

                {/* Side Panel */}
                <div className="space-y-4">
                    {/* Players + Scores */}
                    {[
                        { name: gs?.player_white || 'White', score: gs?.white_score || 0, color: 'W', isActive: gs?.current_player === 'W' && !gs?.is_finished },
                        { name: gs?.player_black || 'Black', score: gs?.black_score || 0, color: 'B', isActive: gs?.current_player === 'B' && !gs?.is_finished },
                    ].map(({ name, score, color, isActive }) => (
                        <div
                            key={color}
                            className="card p-4 transition-all duration-300"
                            style={{
                                borderColor: isActive ? (color === 'W' ? '#e2e8f0' : '#334155') : undefined,
                                boxShadow: isActive ? (color === 'W' ? '0 0 20px rgba(226,232,240,0.3)' : '0 0 20px rgba(51,65,85,0.3)') : undefined,
                            }}
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-8 h-8 rounded-full ${color === 'W' ? 'bg-white border-2 border-slate-300' : 'bg-red-600 border-2 border-red-400'}`} />
                                <div className="flex-1">
                                    <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{name}</p>
                                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                        {isBotGame ? '🤖 Bot' : color === 'W' ? 'White' : 'Black'}
                                        {isActive && botRunning ? ' • Thinking...' : isActive && !isBotGame ? ' • Your turn' : ''}
                                    </p>
                                </div>
                                <div className="text-2xl font-extrabold" style={{ color: 'var(--text-primary)' }}>{score}</div>
                            </div>
                        </div>
                    ))}

                    {/* Progress */}
                    <div className="card p-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Board Progress</span>
                            <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>{progress}%</span>
                        </div>
                        <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                            <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                    width: `${progress}%`,
                                    background: 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                                }}
                            />
                        </div>
                        <p className="mt-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                            {gs?.cells_filled || 0} / {gs?.total_cells || 0} cells filled
                        </p>
                    </div>

                    {/* Bot Running Indicator */}
                    {isBotGame && botRunning && (
                        <div className="card p-4 text-center" style={{ borderColor: '#3b82f6' }}>
                            <div className="inline-block w-5 h-5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin mb-2" />
                            <p className="text-sm font-semibold" style={{ color: '#3b82f6' }}>Bots are playing live</p>
                            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Each move updates the board in real-time</p>
                        </div>
                    )}

                    {/* AI Thinking */}
                    {!isBotGame && thinking && (
                        <div className="card p-4 text-center" style={{ borderColor: '#f59e0b' }}>
                            <div className="inline-block w-5 h-5 border-2 border-gold-400 border-t-transparent rounded-full animate-spin mb-2" />
                            <p className="text-sm font-semibold" style={{ color: '#f59e0b' }}>AI is thinking...</p>
                        </div>
                    )}

                    {/* Game Over Result */}
                    {gs?.is_finished && (
                        <div className="card p-5 text-center" style={{
                            background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.1))',
                            borderColor: '#3b82f6',
                        }}>
                            <p className="text-2xl font-black mb-1" style={{ color: 'var(--text-primary)' }}>
                                {gs.winner === 'draw' ? '🤝 Draw!' : `🏆 ${gs.winner === 'white' ? gs.player_white : gs.player_black} Wins!`}
                            </p>
                            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                Final: {gs.white_score} - {gs.black_score}
                            </p>
                            <button onClick={resetGame} className="btn-primary mt-4">Play Again</button>
                        </div>
                    )}

                    {/* Move Log (Bot vs Bot) */}
                    {isBotGame && moveLog.length > 0 && (
                        <div className="card p-4">
                            <h3 className="text-xs font-bold mb-2" style={{ color: 'var(--text-muted)' }}>
                                MOVE LOG ({moveLog.length} moves)
                            </h3>
                            <div className="max-h-48 overflow-y-auto space-y-0.5 pr-1">
                                {moveLog.map((m, i) => (
                                    <div key={i} className="text-[10px] flex items-center gap-2 py-0.5" style={{ color: 'var(--text-secondary)' }}>
                                        <span className="font-mono font-bold w-5 shrink-0">{i + 1}.</span>
                                        <span className={`w-3 h-3 rounded-full shrink-0 ${m.player === 'W' ? 'bg-white border border-slate-300' : 'bg-red-600 border border-red-400'}`} />
                                        <span className="font-semibold truncate">{m.bot}</span>
                                        <span className="shrink-0">→ {coordLabel(m.row, m.col)}</span>
                                    </div>
                                ))}
                                <div ref={logEndRef} />
                            </div>
                        </div>
                    )}

                    {/* Live Logs (Bot vs Bot) */}
                    {isBotGame && botDebug && (
                        <div className="card p-4">
                            <h3 className="text-xs font-bold mb-2" style={{ color: 'var(--text-muted)' }}>
                                LIVE LOGS
                            </h3>
                            {botDebug.forfeited && (
                                <p className="text-[11px] mb-2 font-semibold" style={{ color: '#ef4444' }}>
                                    Current bot forfeited after {botDebug.max_attempts} failed attempts. Opponent wins.
                                </p>
                            )}
                            {botDebug.attempts && botDebug.attempts.length > 0 && (
                                <>
                                    {botDebug.attempts.slice(-3).map((a) => (
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
                                    ))}
                                </>
                            )}
                            {!botDebug.attempts?.length && (
                                <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                    No bot-step debug info yet.
                                </p>
                            )}
                        </div>
                    )}

                    {/* Scoring Table */}
                    {!isBotGame && (
                        <div className="card p-4">
                            <h3 className="text-xs font-bold mb-2" style={{ color: 'var(--text-muted)' }}>SCORING TABLE</h3>
                            <div className="grid grid-cols-3 gap-1.5">
                                {gs?.scores_for_n && Object.entries(gs.scores_for_n).map(([len, pts]) => (
                                    <div key={len} className="text-center p-1.5 rounded" style={{ background: 'var(--bg-secondary)' }}>
                                        <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Run {len}</div>
                                        <div className="text-xs font-bold" style={{ color: pts > 0 ? '#10b981' : 'var(--text-muted)' }}>
                                            {pts > 0 ? pts : '—'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
