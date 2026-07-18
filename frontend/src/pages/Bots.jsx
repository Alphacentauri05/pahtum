import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getBots, createBot, updateBot, testBot, deleteBot, uploadLocalBot, createInlineBot } from '../api';
import { Bot, Plus, Trash2, Radio, Edit3, TerminalSquare, UploadCloud, CheckCircle2, XCircle, Code2, Play, Swords, ChevronDown, ChevronUp, Code } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const PRESET_TEMPLATE = `"""
Combined Pah Tum Bot Entry - Player 1
Includes core logic, smart playing heuristic, and move wrapper.
"""

import random

# ==========================================
# PAHTUM CORE LOGIC
# ==========================================

SIZE = 7
SEQUENCE_POINTS = (3, 10, 25, 56, 119)

def score_board(board, p1, p2):
    size = len(board)
    count_p1 = [0] * size
    count_p2 = [0] * size

    # Horizontal
    for i in range(size):
        run_p1 = run_p2 = 0
        for j in range(size):
            cell = board[i][j]
            if cell == p1:
                run_p1 += 1; run_p2 = 0
            elif cell == p2:
                run_p2 += 1; run_p1 = 0
            else:
                run_p1 = run_p2 = 0
            if run_p1 >= 3:
                count_p1[run_p1 - 3] += 1
            if run_p2 >= 3:
                count_p2[run_p2 - 3] += 1

    # Vertical
    for j in range(size):
        run_p1 = run_p2 = 0
        for i in range(size):
            cell = board[i][j]
            if cell == p1:
                run_p1 += 1; run_p2 = 0
            elif cell == p2:
                run_p2 += 1; run_p1 = 0
            else:
                run_p1 = run_p2 = 0
            if run_p1 >= 3:
                count_p1[run_p1 - 3] += 1
            if run_p2 >= 3:
                count_p2[run_p2 - 3] += 1

    return count_p1, count_p2

def calculate_scores(board, player1, player2):
    count_p1, count_p2 = score_board(board, player1, player2)
    n = min(len(count_p1), len(SEQUENCE_POINTS))
    s1 = sum(count_p1[i] * SEQUENCE_POINTS[i] for i in range(n))
    s2 = sum(count_p2[i] * SEQUENCE_POINTS[i] for i in range(n))
    return s1, s2

def _opponent_of(stone):
    return {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(stone, 'O')

# ==========================================
# SMART PLAYER LOGIC
# ==========================================

def _copy_board(board):
    return [row[:] for row in board]

def _center_distance(row, col, center=3):
    return abs(row - center) + abs(col - center)

def is_valid_move(board, row, col):
    return 0 <= row < len(board) and 0 <= col < len(board) and board[row][col] == '.'

def _get_valid_moves(board):
    return [(r, c) for r in range(len(board)) for c in range(len(board)) if is_valid_move(board, r, c)]

def heuristic_evaluate(board, player, opponent, offense_weight, defense_weight):
    my_score, opp_score = calculate_scores(board, player, opponent)
    return (my_score * offense_weight) - (opp_score * defense_weight)

def get_heuristic_move(board, player, offense_weight, defense_weight):
    opponent = _opponent_of(player)
    valid_moves = _get_valid_moves(board)
    if not valid_moves:
        return 0, 0

    best_score = float('-inf')
    best_moves = []

    for r, c in valid_moves:
        copy = _copy_board(board)
        copy[r][c] = player
        score = heuristic_evaluate(copy, player, opponent, offense_weight, defense_weight)
        if score > best_score:
            best_score = score
            best_moves = [(r, c)]
        elif score == best_score:
            best_moves.append((r, c))

    center = len(board) // 2
    best_moves.sort(key=lambda rc: _center_distance(rc[0], rc[1], center))
    d0 = _center_distance(best_moves[0][0], best_moves[0][1], center)
    best_moves = [rc for rc in best_moves if _center_distance(rc[0], rc[1], center) == d0]
    return random.choice(best_moves)

def get_smart_move(board, player):
    # TWEAK THESE WEIGHTS TO CREATE YOUR PERSONA
    offense_weight = 1.0
    defense_weight = 1.0
    return get_heuristic_move(board, player, offense_weight, defense_weight)

def bot_move(game_state: dict) -> dict:
    board = game_state["board"]
    player = game_state.get("your_stone", "W")
    r, c = get_smart_move(board, player)
    return {"row": r, "col": c}
`;

export default function Bots() {
    const [bots, setBots] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingBot, setEditingBot] = useState(null);
    const [form, setForm] = useState({ name: '', api_url: '', owner: '', description: '' });
    const [testResults, setTestResults] = useState({});
    const [testing, setTesting] = useState({});
    const [successModal, setSuccessModal] = useState(false);
    const [showWebhookDocs, setShowWebhookDocs] = useState(false);
    
    // Upload Modes
    const [uploadMode, setUploadMode] = useState('code'); // 'code' or 'file'
    const [localForm, setLocalForm] = useState({ name: '', owner: '', description: '', entry_function: 'bot_move', file: null });
    const [code, setCode] = useState(PRESET_TEMPLATE);
    const [codeSubmitting, setCodeSubmitting] = useState(false);

    const load = () => {
        getBots().then(r => setBots(r.data)).catch(() => {}).finally(() => setLoading(false));
    };
    useEffect(load, []);

    const openCreate = () => {
        setEditingBot(null);
        setForm({ name: '', api_url: '', owner: '', description: '' });
        setShowModal(true);
    };

    const openEdit = (bot) => {
        setEditingBot(bot);
        setForm({ name: bot.name, api_url: bot.api_url, owner: bot.owner || '', description: bot.description || '' });
        setShowModal(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.name || !form.api_url) return alert('Name and API URL are required');
        try {
            if (editingBot) await updateBot(editingBot.id, form);
            else await createBot(form);
            setForm({ name: '', api_url: '', owner: '', description: '' });
            setShowModal(false);
            setEditingBot(null);
            load();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed');
        }
    };

    const handleLocalUpload = async (e) => {
        e.preventDefault();
        if (!localForm.name || !localForm.file) return alert('Bot name and Python file are required');
        const fd = new FormData();
        fd.append('name', localForm.name);
        fd.append('owner', localForm.owner);
        fd.append('description', localForm.description);
        fd.append('entry_function', localForm.entry_function || 'bot_move');
        fd.append('file', localForm.file);
        setCodeSubmitting(true);
        try {
            await uploadLocalBot(fd);
            setSuccessModal(true);
            setLocalForm({ name: '', owner: '', description: '', entry_function: 'bot_move', file: null });
            load();
        } catch (err) {
            alert(err.response?.data?.detail || 'Upload failed');
        } finally {
            setCodeSubmitting(false);
        }
    };
    
    const handleCodeSubmit = async (e) => {
        e.preventDefault();
        if (!localForm.name) return alert('Bot name is required');
        if (!code.trim()) return alert('Code cannot be empty');
        setCodeSubmitting(true);
        try {
            await createInlineBot({
                name: localForm.name,
                owner: localForm.owner,
                description: localForm.description,
                entry_function: localForm.entry_function || 'bot_move',
                code: code
            });
            setSuccessModal(true);
            setLocalForm({ name: '', owner: '', description: '', entry_function: 'bot_move', file: null });
            load();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to compile and deploy bot');
        } finally {
            setCodeSubmitting(false);
        }
    };

    const handleTest = async (id) => {
        setTesting(p => ({ ...p, [id]: true }));
        try {
            const res = await testBot(id);
            setTestResults(p => ({ ...p, [id]: res.data }));
        } catch (err) {
            setTestResults(p => ({ ...p, [id]: { success: false, message: 'Request failed' } }));
        } finally {
            setTesting(p => ({ ...p, [id]: false }));
            load();
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this bot?')) return;
        try { await deleteBot(id); load(); } catch { alert('Failed to delete bot'); }
    };

    const statusColors = {
        online: 'bg-emerald-400', 
        offline: 'bg-red-400', 
        timeout: 'bg-amber-400', 
        error: 'bg-red-400', 
        registered: 'bg-blue-400'
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8 animate-in">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400">AI Agents</h1>
                    <p className="mt-1 text-white/60">Deploy and manage your competitive AI bots</p>
                </div>
                <button onClick={openCreate} className="glass-button glass-button-secondary flex items-center gap-2 border-primary/30 hover:border-primary/60">
                    <TerminalSquare size={18} className="text-primary" /> Setup Webhook API
                </button>
            </div>

            <div className="glass-panel overflow-hidden border-emerald-500/30">
                <div className="flex border-b border-white/10 bg-black/40">
                    <button 
                        onClick={() => setUploadMode('code')} 
                        className={`flex-1 py-4 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${uploadMode === 'code' ? 'text-emerald-400 border-b-2 border-emerald-500 bg-white/5' : 'text-white/50 hover:text-white/80'}`}
                    >
                        <Code2 size={18} /> IDE: Write Bot Inline
                    </button>
                    <button 
                        onClick={() => setUploadMode('file')} 
                        className={`flex-1 py-4 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${uploadMode === 'file' ? 'text-emerald-400 border-b-2 border-emerald-500 bg-white/5' : 'text-white/50 hover:text-white/80'}`}
                    >
                        <UploadCloud size={18} /> Upload Local Script (.py)
                    </button>
                </div>
                
                <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Form Left Side */}
                    <div className="lg:col-span-4 space-y-4">
                        <div>
                            <label className="block text-xs font-semibold text-white/70 mb-1">Agent Name *</label>
                            <input className="glass-input w-full bg-black/30" placeholder="e.g. AlphaTum" value={localForm.name} onChange={e => setLocalForm(f => ({ ...f, name: e.target.value }))} required />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-white/70 mb-1">Description</label>
                            <textarea className="glass-input w-full h-24 resize-none bg-black/30" placeholder="Agent strategy..." value={localForm.description} onChange={e => setLocalForm(f => ({ ...f, description: e.target.value }))} />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-semibold text-white/70 mb-1">Owner</label>
                                <input className="glass-input w-full bg-black/30" value={localForm.owner} onChange={e => setLocalForm(f => ({ ...f, owner: e.target.value }))} />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-white/70 mb-1">Entry Func</label>
                                <input className="glass-input w-full bg-black/30" value={localForm.entry_function} onChange={e => setLocalForm(f => ({ ...f, entry_function: e.target.value }))} />
                            </div>
                        </div>
                        
                        {uploadMode === 'file' && (
                            <div className="pt-2">
                                <label className="block text-xs font-semibold text-white/70 mb-1">Python File (*.py) *</label>
                                <input 
                                    type="file" accept=".py" required
                                    className="block w-full text-sm text-white/60 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-emerald-500/20 file:text-emerald-400 hover:file:bg-emerald-500/30 cursor-pointer"
                                    onChange={e => setLocalForm(f => ({ ...f, file: e.target.files?.[0] || null }))}
                                />
                            </div>
                        )}

                        <button 
                            onClick={uploadMode === 'code' ? handleCodeSubmit : handleLocalUpload} 
                            disabled={codeSubmitting}
                            className="glass-button w-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] border-none mt-4 disabled:opacity-50"
                        >
                            {codeSubmitting ? (
                                <div className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                            ) : (
                                <><Play size={18} fill="currentColor" /> Deploy Agent to Server</>
                            )}
                        </button>
                    </div>

                    {/* Editor Right Side */}
                    <div className="lg:col-span-8">
                        {uploadMode === 'code' ? (
                            <div className="h-[500px] rounded-xl overflow-hidden border border-white/10 bg-[#0d0d14] flex flex-col shadow-inner">
                                <div className="bg-black/40 px-4 py-2 border-b border-white/5 flex items-center justify-between">
                                    <span className="text-xs font-mono text-white/50">agent_logic.py</span>
                                    <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">Python 3.11 Environment</span>
                                </div>
                                <textarea 
                                    className="flex-1 w-full p-4 bg-transparent text-emerald-300 font-mono text-sm leading-relaxed focus:outline-none resize-none custom-scrollbar"
                                    spellCheck="false"
                                    value={code}
                                    onChange={e => setCode(e.target.value)}
                                />
                            </div>
                        ) : (
                            <div className="h-[500px] rounded-xl border border-white/10 bg-black/20 flex flex-col items-center justify-center text-center p-8">
                                <UploadCloud size={64} className="text-white/10 mb-4" />
                                <h3 className="text-lg font-bold text-white/70 mb-2">Upload Local Script</h3>
                                <p className="text-sm text-white/40 max-w-sm">
                                    Your uploaded script must contain the entry function defined in the panel to the left. The default is <code>bot_move(game_state)</code>.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Bots List */}
            <div>
                <h2 className="text-xl font-bold text-white mb-4">Your Agents</h2>
                {loading ? (
                    <div className="flex justify-center p-8"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div></div>
                ) : bots.length === 0 ? (
                    <div className="glass-panel p-12 text-center">
                        <Bot className="w-16 h-16 mx-auto mb-4 text-white/20" />
                        <h3 className="text-xl font-semibold text-white mb-2">No Agents Deployed</h3>
                        <p className="text-white/60">Upload a Python script or write code inline to get started.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {bots.map(bot => (
                            <motion.div initial={{opacity:0, scale:0.95}} animate={{opacity:1, scale:1}} key={bot.id} className="glass-panel p-5 relative overflow-hidden group hover:border-white/20">
                                <div className={`absolute top-0 left-0 w-1 h-full ${statusColors[bot.status] || 'bg-blue-400'}`} />
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-lg font-bold text-white">{bot.name}</h3>
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-white/10 ${statusColors[bot.status]?.replace('bg-', 'text-') || 'text-blue-400'}`}>
                                                {bot.status}
                                            </span>
                                        </div>
                                        <p className="text-xs text-white/50">{bot.type === 'local_py' ? 'Python Script (Hosted)' : bot.api_url}</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={() => handleTest(bot.id)} disabled={testing[bot.id]} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-blue-400 transition-colors" title="Ping Agent">
                                            {testing[bot.id] ? <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" /> : <Radio size={16} />}
                                        </button>
                                        <button onClick={() => openEdit(bot)} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Edit Meta">
                                            <Edit3 size={16} />
                                        </button>
                                        <button onClick={() => handleDelete(bot.id)} className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors" title="Delete">
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>

                                <div className="flex gap-6 mb-4">
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-emerald-400">{bot.wins}</div>
                                        <div className="text-[10px] text-white/50 uppercase tracking-widest">Wins</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-red-400">{bot.losses}</div>
                                        <div className="text-[10px] text-white/50 uppercase tracking-widest">Losses</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-blue-400">{bot.draws}</div>
                                        <div className="text-[10px] text-white/50 uppercase tracking-widest">Draws</div>
                                    </div>
                                </div>

                                {testResults[bot.id] && (
                                    <div className={`p-3 rounded-lg text-xs flex items-start gap-2 ${testResults[bot.id].success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                        {testResults[bot.id].success ? <CheckCircle2 size={14} className="shrink-0 mt-0.5" /> : <XCircle size={14} className="shrink-0 mt-0.5" />}
                                        <span>{testResults[bot.id].message}</span>
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>

            {/* API Webhook Modal */}
            <AnimatePresence>
                {showModal && (
                    <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowModal(false)}>
                        <motion.div initial={{scale:0.95}} animate={{scale:1}} exit={{scale:0.95}} className="glass-panel p-8 w-full max-w-md m-4" onClick={e => e.stopPropagation()}>
                            <h2 className="text-xl font-bold text-white mb-6">{editingBot ? 'Edit API Agent' : 'Register API Agent'}</h2>
                            <div className="mb-4">
                                <button onClick={() => setShowWebhookDocs(!showWebhookDocs)} className="flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300 font-bold transition-colors">
                                    <Code size={16} /> How to write a Webhook Agent {showWebhookDocs ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </button>
                                <AnimatePresence>
                                    {showWebhookDocs && (
                                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                                            <div className="mt-3 p-3 rounded-lg bg-black/40 border border-white/10 text-[11px] font-mono text-emerald-100/70 space-y-2">
                                                <p><span className="text-emerald-400">POST</span> to your webhook with this JSON:</p>
                                                <pre className="bg-black/60 p-2 rounded text-blue-300">
{`{
  "board": [[".", "W", "."], ...],
  "board_size": 7,
  "your_stone": "B",
  "opponent_stone": "W",
  "turn": 4,
  ...
}`}
                                                </pre>
                                                <p>You must reply within 5s with your move:</p>
                                                <pre className="bg-black/60 p-2 rounded text-emerald-300">
{`{
  "row": 3,
  "col": 4
}`}
                                                </pre>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-xs font-semibold text-white/70 mb-1">Bot Name *</label>
                                    <input className="glass-input w-full" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-white/70 mb-1">Webhook URL *</label>
                                    <input className="glass-input w-full" placeholder="https://your-server.com/move" value={form.api_url} onChange={e => setForm(f => ({ ...f, api_url: e.target.value }))} required />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-xs font-semibold text-white/70 mb-1">Owner</label>
                                        <input className="glass-input w-full" placeholder="Optional" value={form.owner} onChange={e => setForm(f => ({ ...f, owner: e.target.value }))} />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-semibold text-white/70 mb-1">Description</label>
                                        <input className="glass-input w-full" placeholder="Optional" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                                    </div>
                                </div>
                                <div className="flex gap-3 pt-4">
                                    <button type="button" onClick={() => setShowModal(false)} className="glass-button glass-button-secondary flex-1">Cancel</button>
                                    <button type="submit" className="glass-button glass-button-primary flex-1">{editingBot ? 'Save Changes' : 'Register Webhook'}</button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Success Modal */}
            <AnimatePresence>
                {successModal && (
                    <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setSuccessModal(false)}>
                        <motion.div initial={{scale:0.95}} animate={{scale:1}} exit={{scale:0.95}} className="glass-panel p-8 w-full max-w-md m-4 text-center" onClick={e => e.stopPropagation()}>
                            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                                <CheckCircle2 size={32} className="text-emerald-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">Agent Approved & Deployed!</h2>
                            <p className="text-white/60 mb-8">
                                Your algorithm was compiled successfully and is now active on the server. You can now select it as a player in your upcoming matches.
                            </p>
                            <div className="flex gap-3">
                                <button onClick={() => setSuccessModal(false)} className="glass-button glass-button-secondary flex-1">Stay Here</button>
                                <Link to="/play" className="glass-button glass-button-primary flex-1 flex items-center justify-center gap-2">
                                    <Swords size={18} /> Enter Arena
                                </Link>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
