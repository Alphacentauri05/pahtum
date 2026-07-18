import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import api from '../api';
import { motion } from 'framer-motion';
import { Play, Bot, Trophy, Users, Code2, Cpu, Zap, ArrowRight, ShieldCheck, Swords } from 'lucide-react';

export default function Dashboard() {
    const { user } = useAuth();
    const [stats, setStats] = useState({ total_players: 0, total_tournaments: 0, matches_played: 0, active_tournaments: 0 });
    const [topPlayers, setTopPlayers] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.get('/leaderboard').then(res => setTopPlayers(res.data.slice(0, 5))).catch(() => {}),
            // Fetch stats if available, mock for now to match UI
            Promise.resolve({ total_players: 142, total_tournaments: 12, matches_played: 3420, active_tournaments: 3 })
        ]).then(([, mockStats]) => {
            setStats(mockStats);
            setLoading(false);
        });
    }, []);

    const statCards = [
        { label: 'Global Engineers', value: stats.total_players, icon: Users, color: 'text-blue-400', bg: 'bg-blue-400/10' },
        { label: 'Total Tournaments', value: stats.total_tournaments, icon: Trophy, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
        { label: 'Matches Simulated', value: stats.matches_played, icon: Play, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
        { label: 'Active Events', value: stats.active_tournaments, icon: Zap, color: 'text-purple-400', bg: 'bg-purple-400/10' },
    ];

    if (!user) {
        return (
            <div className="w-full flex flex-col items-center justify-center text-center mt-12 mb-24 animate-in fade-in duration-700">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-panel border-purple-500/30 text-purple-300 text-xs font-bold mb-8 uppercase tracking-widest">
                    <Sparkles size={14} /> The Ultimate AI Battleground
                </motion.div>
                
                <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }} className="text-5xl md:text-7xl font-extrabold text-white tracking-tight leading-[1.1] mb-6">
                    Code. Compete. <br className="hidden md:block" />
                    <span className="text-gradient-primary">Conquer.</span>
                </motion.h1>
                
                <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }} className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed">
                    Build autonomous AI agents for the ancient game of Pah-Tum. Deploy your python algorithms, test them in the arena, and climb the global engineering leaderboard.
                </motion.p>
                
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.3 }} className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto justify-center">
                    <Link to="/signup" className="glass-button glass-button-primary !px-8 !py-4 text-lg">
                        Start Building Free <ArrowRight size={20} />
                    </Link>
                    <Link to="/leaderboard" className="glass-button glass-button-secondary !px-8 !py-4 text-lg">
                        View Leaderboard
                    </Link>
                </motion.div>

                {/* Hero Stats */}
                <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.5 }} className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-4xl mt-24">
                    {statCards.map((stat, i) => (
                        <div key={i} className="glass-panel p-6 text-center">
                            <div className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center mb-4 ${stat.bg} ${stat.color}`}>
                                <stat.icon size={24} />
                            </div>
                            <h3 className="text-3xl font-black text-white mb-1">{stat.value.toLocaleString()}</h3>
                            <p className="text-xs font-bold text-white/40 uppercase tracking-widest">{stat.label}</p>
                        </div>
                    ))}
                </motion.div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-extrabold text-white tracking-tight mb-2">
                        Welcome back, <span className="text-gradient-primary">{user.username}</span>
                    </h1>
                    <p className="text-white/60 text-lg">
                        Your engineering command center.
                    </p>
                </div>
                <div className="flex gap-3">
                    <Link to="/bots" className="glass-button glass-button-secondary">
                        <Code2 size={18} /> Manage Agents
                    </Link>
                    <Link to="/play" className="glass-button glass-button-primary">
                        <Swords size={18} /> Arena
                    </Link>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                {statCards.map((stat, index) => (
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}
                        key={index} 
                        className="glass-panel p-6 flex items-center gap-4 group"
                    >
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-110 duration-300 ${stat.bg} ${stat.color}`}>
                            <stat.icon size={28} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-white/50 uppercase tracking-wider mb-1">{stat.label}</p>
                            <h3 className="text-3xl font-black text-white leading-none">
                                {loading ? '-' : stat.value.toLocaleString()}
                            </h3>
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
                {/* Agent Operations */}
                <div className="glass-panel p-8 lg:col-span-2 flex flex-col justify-between relative overflow-hidden group">
                    <div className="absolute -right-20 -top-20 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl group-hover:bg-purple-500/20 transition-all duration-700" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-6 shadow-lg shadow-purple-500/25">
                            <Cpu size={24} className="text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Deploy AI Agents</h2>
                        <p className="text-white/60 mb-8 max-w-md leading-relaxed">
                            Upload your Python script or connect an external HTTP API. Test your agent's logic in the sandbox before entering official tournaments.
                        </p>
                        
                        <div className="grid sm:grid-cols-2 gap-4">
                            <Link to="/bots" className="glass-button bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 text-white flex flex-col items-start p-6 h-auto gap-4">
                                <div className="w-10 h-10 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center">
                                    <Code2 size={20} />
                                </div>
                                <div className="text-left">
                                    <h4 className="font-bold text-lg mb-1">Agent Config</h4>
                                    <p className="text-xs text-white/50 font-normal">Manage endpoints and scripts</p>
                                </div>
                            </Link>
                            <Link to="/play" className="glass-button bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 text-white flex flex-col items-start p-6 h-auto gap-4">
                                <div className="w-10 h-10 rounded-full bg-pink-500/20 text-pink-400 flex items-center justify-center">
                                    <Swords size={20} />
                                </div>
                                <div className="text-left">
                                    <h4 className="font-bold text-lg mb-1">Test Arena</h4>
                                    <p className="text-xs text-white/50 font-normal">Simulate matches instantly</p>
                                </div>
                            </Link>
                        </div>
                    </div>
                </div>

                {/* Leaderboard Snippet */}
                <div className="glass-panel p-0 flex flex-col overflow-hidden">
                    <div className="p-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                        <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <Trophy size={20} className="text-yellow-400" /> Top Engineers
                        </h2>
                        <Link to="/leaderboard" className="text-xs font-bold text-purple-400 hover:text-purple-300">View All</Link>
                    </div>
                    
                    <div className="p-4 flex-1">
                        {loading ? (
                            <div className="flex justify-center p-8"><div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" /></div>
                        ) : topPlayers.length === 0 ? (
                            <div className="text-center p-8 text-white/40 text-sm font-medium">No ranked players yet.</div>
                        ) : (
                            <div className="space-y-2">
                                {topPlayers.map((p, idx) => (
                                    <div key={p.id} className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors">
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${idx === 0 ? 'bg-yellow-400/20 text-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.2)]' : idx === 1 ? 'bg-slate-300/20 text-slate-300' : idx === 2 ? 'bg-amber-600/20 text-amber-500' : 'bg-white/5 text-white/50'}`}>
                                            #{idx + 1}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-bold text-white truncate">{p.username}</p>
                                            <p className="text-[10px] font-bold text-emerald-400 uppercase">{p.wins} W / {p.losses} L</p>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <p className="text-sm font-black text-white">{p.total_score}</p>
                                            <p className="text-[9px] font-bold text-white/40 uppercase tracking-wider">Score</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function Sparkles(props) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
            <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
        </svg>
    );
}
