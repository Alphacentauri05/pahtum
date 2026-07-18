import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTournaments, createTournament, editTournament, deleteTournament } from '../api';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Plus, Pencil, Trash2, Users, LayoutGrid, AlertCircle, Swords } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Tournaments() {
    const { user } = useAuth();
    const [tournaments, setTournaments] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [editingTournament, setEditingTournament] = useState(null);
    const [form, setForm] = useState({ name: '', description: '', board_size: 7, max_players: 16, format: 'knockout' });
    const [loading, setLoading] = useState(true);

    const load = () => {
        getTournaments()
            .then(res => setTournaments(res.data))
            .catch(() => { })
            .finally(() => setLoading(false));
    }
    useEffect(load, []);

    const openCreate = () => {
        setEditingTournament(null);
        setForm({ name: '', description: '', board_size: 7, max_players: 16, format: 'knockout' });
        setShowModal(true);
    }

    const openEdit = (e, t) => {
        e.preventDefault();
        e.stopPropagation();
        setEditingTournament(t);
        setForm({ name: t.name, description: t.description || '', board_size: t.board_size, max_players: t.max_players, format: t.format || 'knockout' });
        setShowModal(true);
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingTournament) {
                await editTournament(editingTournament.id, form);
            } else {
                await createTournament(form);
            }
            setShowModal(false);
            setEditingTournament(null);
            load();
        } catch (err) {
            alert(err.response?.data?.detail || 'Error');
        }
    }

    const handleDelete = async (e, t) => {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm(`Delete "${t.name}"? This cannot be undone.`)) return;
        try {
            await deleteTournament(t.id);
            load();
        } catch (err) {
            alert(err.response?.data?.detail || 'Error');
        }
    }

    const statusBadge = (status) => {
        const badges = {
            upcoming: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400' },
            active: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400' },
            completed: { bg: 'bg-white/5', border: 'border-white/10', text: 'text-white/50' }
        };
        const style = badges[status] || badges.upcoming;
        return (
            <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${style.bg} ${style.border} ${style.text}`}>
                {status}
            </span>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-extrabold text-white tracking-tight mb-2">
                        Official <span className="text-gradient-primary">Tournaments</span>
                    </h1>
                    <p className="text-white/60 text-lg">
                        Compete in Pah-Tum ranked engineering events.
                    </p>
                </div>
                {user?.role === 'ADMIN' && (
                    <button onClick={openCreate} className="glass-button glass-button-primary">
                        <Plus size={18} /> New Event
                    </button>
                )}
            </div>

            {loading ? (
                <div className="flex justify-center p-20">
                    <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(168,85,247,0.5)]" />
                </div>
            ) : tournaments.length === 0 ? (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-16 text-center max-w-2xl mx-auto mt-12">
                    <div className="w-20 h-20 mx-auto rounded-full bg-white/5 flex items-center justify-center mb-6">
                        <Trophy size={40} className="text-white/30" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-3">No Active Tournaments</h3>
                    <p className="text-white/50 mb-8 max-w-md mx-auto">
                        There are currently no official tournaments running. {user?.role === 'ADMIN' && "Create one to get started!"}
                    </p>
                    {user?.role === 'ADMIN' && (
                        <button onClick={openCreate} className="glass-button glass-button-primary mx-auto">
                            <Plus size={18} /> Create First Tournament
                        </button>
                    )}
                </motion.div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {tournaments.map((t, index) => (
                        <motion.div 
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
                            key={t.id} 
                        >
                            <Link to={`/tournaments/${t.id}`} className="glass-panel p-6 group block h-full flex flex-col hover:border-purple-500/30">
                                {/* Admin Controls on Hover */}
                                {user?.role === 'ADMIN' && (
                                    <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 translate-y-1 group-hover:translate-y-0">
                                        <button onClick={(e) => openEdit(e, t)} className="w-8 h-8 rounded-full bg-black/50 border border-white/10 flex items-center justify-center text-white/70 hover:text-white hover:bg-purple-500/20 hover:border-purple-500/50 transition-all backdrop-blur-md" title="Edit">
                                            <Pencil size={14} />
                                        </button>
                                        <button onClick={(e) => handleDelete(e, t)} className="w-8 h-8 rounded-full bg-black/50 border border-white/10 flex items-center justify-center text-red-400 hover:text-white hover:bg-red-500/80 hover:border-red-500 transition-all backdrop-blur-md" title="Delete">
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                )}
                                
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-400/20 to-orange-500/20 border border-yellow-500/20 flex items-center justify-center shadow-[0_0_15px_rgba(250,204,21,0.15)] group-hover:shadow-[0_0_25px_rgba(250,204,21,0.3)] transition-all">
                                        <Trophy size={24} className="text-yellow-400" />
                                    </div>
                                    {statusBadge(t.status)}
                                </div>
                                
                                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                                    {t.name}
                                </h3>
                                <p className="text-sm text-white/50 mb-6 flex-1 line-clamp-2">
                                    {t.description || 'A ranked engineering competition.'}
                                </p>
                                
                                <div className="flex items-center gap-4 border-t border-white/5 pt-4 mt-auto">
                                    <div className="flex items-center gap-1.5 text-xs font-semibold text-white/60" title="Format">
                                        <Swords size={14} className="text-pink-400" />
                                        {t.format === 'group_stage' ? 'Group Stage' : 'Knockout'}
                                    </div>
                                    <div className="flex items-center gap-1.5 text-xs font-semibold text-white/60" title="Board Size">
                                        <LayoutGrid size={14} className="text-blue-400" />
                                        {t.board_size}×{t.board_size}
                                    </div>
                                    <div className="flex items-center gap-1.5 text-xs font-semibold text-white/60 ml-auto" title="Participants">
                                        <Users size={14} className="text-emerald-400" />
                                        {t.player_count}/{t.max_players}
                                    </div>
                                </div>
                            </Link>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            <AnimatePresence>
                {showModal && (
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" 
                        onClick={() => setShowModal(false)}
                    >
                        <motion.div 
                            initial={{ scale: 0.95, opacity: 0, y: 20 }} 
                            animate={{ scale: 1, opacity: 1, y: 0 }} 
                            exit={{ scale: 0.95, opacity: 0, y: 20 }}
                            className="glass-panel p-8 w-full max-w-md border-purple-500/30 shadow-[0_0_50px_rgba(168,85,247,0.15)]" 
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
                                    {editingTournament ? <Pencil size={20} /> : <Plus size={20} />}
                                </div>
                                <h2 className="text-2xl font-bold text-white">
                                    {editingTournament ? 'Edit Tournament' : 'New Tournament'}
                                </h2>
                            </div>
                            
                            <form onSubmit={handleSubmit} className="space-y-5">
                                {!editingTournament && (
                                    <div>
                                        <label className="block text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Format</label>
                                        <div className="flex gap-2">
                                            {[['knockout', 'Knockout'], ['group_stage', 'Group Stage']].map(([val, label]) => (
                                                <button key={val} type="button" onClick={() => setForm({ ...form, format: val })}
                                                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${
                                                        form.format === val 
                                                            ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]' 
                                                            : 'bg-white/5 text-white/50 hover:bg-white/10 hover:text-white'
                                                    }`}>
                                                    {val === 'knockout' ? <Swords size={16} /> : <Users size={16} />}
                                                    {label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div>
                                    <label className="block text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Tournament Name</label>
                                    <input className="glass-input" placeholder="e.g. Pah-Tum Championship 2026" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Description</label>
                                    <textarea className="glass-input h-24 resize-none" placeholder="What are the stakes?" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Board Size</label>
                                        <select className="glass-input appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FFFFFF%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')] bg-no-repeat bg-[length:10px_10px] bg-[position:right_1rem_center]" value={form.board_size} onChange={e => setForm({ ...form, board_size: parseInt(e.target.value) })}>
                                            {[3, 4, 5, 6, 7, 8, 9, 10].map(n => (<option key={n} value={n} className="bg-slate-900 text-white">{n}×{n}</option>))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Max Agents</label>
                                        <select className="glass-input appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FFFFFF%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')] bg-no-repeat bg-[length:10px_10px] bg-[position:right_1rem_center]" value={form.max_players} onChange={e => setForm({ ...form, max_players: parseInt(e.target.value) })}>
                                            {[4, 8, 16, 32, 64].map(n => (<option key={n} value={n} className="bg-slate-900 text-white">{n} Bots</option>))}
                                        </select>
                                    </div>
                                </div>
                                
                                {user?.role !== 'ADMIN' && (
                                    <div className="bg-orange-500/10 border border-orange-500/20 text-orange-400 p-3 rounded-lg text-xs flex items-start gap-2">
                                        <AlertCircle size={16} className="shrink-0 mt-0.5" />
                                        <p>Only Administrators can create official tournaments. Your actions here will be restricted.</p>
                                    </div>
                                )}

                                <div className="flex gap-3 pt-4">
                                    <button type="button" onClick={() => setShowModal(false)} className="glass-button glass-button-secondary flex-1">Cancel</button>
                                    <button type="submit" className="glass-button glass-button-primary flex-1">{editingTournament ? 'Save Changes' : 'Create Event'}</button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
