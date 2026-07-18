import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { newGame, makeMove, getAiMove, getPlayers, getBots, botStep } from '../api';
import GameBoard from '../components/GameBoard';
import WinPredictor from '../components/WinPredictor';
import { Swords, Bot, Settings2, Play, RotateCcw, AlertTriangle, TerminalSquare } from 'lucide-react';
import { motion } from 'framer-motion';

export default function PlayGame() {
    const [searchParams] = useSearchParams();
    const [gameState, setGameState] = useState(null);
    const [setup, setSetup] = useState({
        board_size: parseInt(searchParams.get('board')) || 7,
        mode: 'bot_vs_bot',
        player_white: 'Bot A',
        player_black: 'Bot B',
    });
    const [bots, setBots] = useState([]);
    const [botWhiteId, setBotWhiteId] = useState('');
    const [botBlackId, setBotBlackId] = useState('');
    const [started, setStarted] = useState(false);
    const [thinking, setThinking] = useState(false);
    const [lastMove, setLastMove] = useState(null);

    const [moveLog, setMoveLog] = useState([]);
    const [botRunning, setBotRunning] = useState(false);
    const [botDebug, setBotDebug] = useState(null);
    const stopRef = useRef(false);
    const logEndRef = useRef(null);

    useEffect(() => {
        getBots().then(res => setBots(res.data)).catch(console.error);
    }, []);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [moveLog]);

    const startGame = async () => {
        if (setup.mode === 'bot_vs_bot') {
            if (!botWhiteId || !botBlackId) return alert('Select both bots');
            if (botWhiteId === botBlackId) return alert('Select two different bots');

            try {
                const res = await newGame({
                    board_size: setup.board_size,
                    mode: 'bot_vs_bot',
                    player_white: bots.find(b => b.id === botWhiteId)?.name || 'Bot A',
                    player_black: bots.find(b => b.id === botBlackId)?.name || 'Bot B',
                    bot_white_id: botWhiteId,
                    bot_black_id: botBlackId,
                });
                setGameState(res.data);
                setStarted(true);
                setMoveLog([]);
                setLastMove(null);
                stopRef.current = false;
                runBotLoop(res.data.game_id);
            } catch (err) {
                alert(err.response?.data?.detail || 'Failed to start game');
            }
        }
    };

    const runBotLoop = async (gameId) => {
        setBotRunning(true);
        let finished = false;

        while (!finished && !stopRef.current) {
            try {
                const res = await botStep(gameId);
                const state = res.data;
                setGameState(state);
                if (state.bot_step_debug) setBotDebug(state.bot_step_debug);

                if (state.last_move) {
                    setLastMove({ row: state.last_move.row, col: state.last_move.col });
                    setMoveLog(prev => [...prev, state.last_move]);
                }

                if (state.is_finished) finished = true;
            } catch (err) {
                console.error('Bot step failed:', err);
                finished = true;
            }
        }
        setBotRunning(false);
    };

    const resetGame = () => {
        stopRef.current = true;
        setGameState(null);
        setStarted(false);
        setLastMove(null);
        setThinking(false);
        setMoveLog([]);
        setBotRunning(false);
        setBotDebug(null);
    };

    if (!started) {
        return (
            <div className="max-w-4xl mx-auto animate-in">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400 mb-2">
                        Testing Arena
                    </h1>
                    <p className="text-white/60">Configure your match and let the AI battle begin.</p>
                </div>

                <div className="glass-panel p-8 max-w-2xl mx-auto">
                    <div className="mb-8">
                        <label className="block text-sm font-semibold text-white/70 mb-3 flex items-center gap-2">
                            <Settings2 size={18} /> Board Size
                        </label>
                        <div className="flex flex-wrap gap-3">
                            {[5, 7, 9].map(n => (
                                <button
                                    key={n}
                                    onClick={() => setSetup(s => ({ ...s, board_size: n }))}
                                    className={`w-14 h-14 rounded-xl font-bold text-lg transition-all duration-300 ${
                                        setup.board_size === n 
                                        ? 'bg-gradient-to-br from-primary to-purple-600 text-white shadow-lg shadow-primary/25 border-transparent' 
                                        : 'bg-white/5 text-white/70 hover:bg-white/10 border border-white/10'
                                    }`}
                                >
                                    {n}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <label className="block text-sm font-semibold text-white/70 mb-2 flex items-center gap-2">
                                <span className="w-3 h-3 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.5)]" /> White Agent
                            </label>
                            <select
                                className="glass-input w-full mt-2 bg-black/40 text-white border-white/10"
                                value={botWhiteId}
                                onChange={e => setBotWhiteId(e.target.value)}
                            >
                                <option value="" className="bg-black text-slate-400">Select an Agent...</option>
                                {bots.map(b => (
                                    <option key={b.id} value={b.id} className="bg-black text-white">{b.name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <label className="block text-sm font-semibold text-white/70 mb-2 flex items-center gap-2">
                                <span className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]" /> Black Agent
                            </label>
                            <select
                                className="glass-input w-full mt-2 bg-black/40 text-white border-white/10"
                                value={botBlackId}
                                onChange={e => setBotBlackId(e.target.value)}
                            >
                                <option value="" className="bg-black text-slate-400">Select an Agent...</option>
                                {bots.map(b => (
                                    <option key={b.id} value={b.id} className="bg-black text-white">{b.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <button onClick={startGame} className="glass-button glass-button-primary w-full text-lg py-4 flex items-center justify-center gap-3">
                        <Swords size={24} /> Enter Arena
                    </button>
                </div>
            </div>
        );
    }

    const gs = gameState;
    const progress = gs ? Math.round((gs.cells_filled / gs.total_cells) * 100) : 0;

    return (
        <div className="max-w-6xl mx-auto space-y-6 animate-in">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-extrabold text-white flex items-center gap-3">
                        {gs?.is_finished ? '🏆 Match Concluded' : '⚔️ Live Battle'}
                        {botRunning && <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />}
                    </h1>
                </div>
                <button onClick={resetGame} className="glass-button glass-button-secondary flex items-center gap-2">
                    <RotateCcw size={16} /> End Simulation
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-8">
                {/* Board */}
                <div className="glass-panel p-8 flex flex-col items-center justify-center min-h-[600px] relative">
                    <WinPredictor gameState={gs} />
                    <GameBoard
                        board={gs?.board}
                        boardSize={gs?.board_size || setup.board_size}
                        currentPlayer={gs?.current_player}
                        onCellClick={() => {}}
                        disabled={true}
                        lastMove={lastMove}
                    />
                    
                    {gs?.is_finished && (
                        <motion.div initial={{opacity:0, scale:0.9}} animate={{opacity:1, scale:1}} className="absolute inset-0 z-10 flex items-center justify-center bg-black/60 backdrop-blur-md rounded-2xl">
                            <div className="text-center">
                                <h2 className="text-5xl font-black text-white mb-4 drop-shadow-[0_0_20px_rgba(255,255,255,0.3)]">
                                    {gs.winner === 'draw' ? 'DRAW' : gs.winner === 'white' ? 'WHITE WINS' : 'BLACK WINS'}
                                </h2>
                                <p className="text-2xl text-white/80 font-bold mb-8">
                                    {gs.white_score} - {gs.black_score}
                                </p>
                                <button onClick={resetGame} className="glass-button glass-button-primary px-8">New Match</button>
                            </div>
                        </motion.div>
                    )}
                </div>

                {/* Info Panel */}
                <div className="space-y-6">
                    {/* Scores */}
                    <div className="grid grid-cols-2 gap-4">
                        {[
                            { name: gs?.player_white || 'White', score: gs?.white_score || 0, color: 'W', active: gs?.current_player === 'W' && !gs?.is_finished },
                            { name: gs?.player_black || 'Black', score: gs?.black_score || 0, color: 'B', active: gs?.current_player === 'B' && !gs?.is_finished },
                        ].map(({ name, score, color, active }) => (
                            <div key={color} className={`glass-panel p-4 text-center transition-all duration-300 ${active ? 'border-primary ring-2 ring-primary/20 bg-primary/10' : ''}`}>
                                <div className={`w-10 h-10 mx-auto rounded-full mb-3 flex items-center justify-center ${color === 'W' ? 'bg-white shadow-[0_0_15px_rgba(255,255,255,0.4)]' : 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.4)]'}`}>
                                    <Bot size={20} className={color === 'W' ? 'text-black' : 'text-white'} />
                                </div>
                                <div className="text-3xl font-black text-white mb-1">{score}</div>
                                <div className="text-xs font-semibold text-white/60 uppercase truncate px-2">{name}</div>
                            </div>
                        ))}
                    </div>

                    {/* Terminal / Live Logs */}
                    <div className="glass-panel p-4 h-[400px] flex flex-col font-mono">
                        <div className="flex items-center gap-2 mb-4 text-primary font-bold text-sm border-b border-white/10 pb-2">
                            <TerminalSquare size={16} /> Console Output
                        </div>
                        <div className="flex-1 overflow-y-auto space-y-2 pr-2 text-xs">
                            {moveLog.map((m, i) => (
                                <div key={i} className="flex items-center gap-3 text-white/70">
                                    <span className="text-white/30 shrink-0">[{String(i+1).padStart(3, '0')}]</span>
                                    <span className={`w-2 h-2 rounded-full shrink-0 ${m.player === 'W' ? 'bg-white' : 'bg-red-500'}`} />
                                    <span className="truncate flex-1">{m.bot}</span>
                                    <span className="text-emerald-400 shrink-0">→ {String.fromCharCode(65 + m.row)}{m.col + 1}</span>
                                </div>
                            ))}
                            {botDebug?.attempts?.map((a, idx) => (
                                <div key={`err-${idx}`} className="flex items-start gap-2 text-red-400 mt-2 bg-red-500/10 p-2 rounded">
                                    <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                                    <span>Error processing bot response: {a.error_type} - {a.message}</span>
                                </div>
                            ))}
                            <div ref={logEndRef} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
