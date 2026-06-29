import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getTournaments, createTournament, editTournament, deleteTournament } from '../api'
import { HiOutlinePlus, HiOutlineTrophy, HiOutlinePencil, HiOutlineTrash } from 'react-icons/hi2'

export default function Tournaments() {
    const [tournaments, setTournaments] = useState([])
    const [showModal, setShowModal] = useState(false)
    const [editingTournament, setEditingTournament] = useState(null)
    const [form, setForm] = useState({ name: '', description: '', board_size: 7, max_players: 16, format: 'knockout' })
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()

    const load = () => {
        getTournaments()
            .then(res => setTournaments(res.data))
            .catch(() => { })
            .finally(() => setLoading(false))
    }
    useEffect(load, [])

    const openCreate = () => {
        setEditingTournament(null)
        setForm({ name: '', description: '', board_size: 7, max_players: 16, format: 'knockout' })
        setShowModal(true)
    }

    const openEdit = (e, t) => {
        e.preventDefault()
        e.stopPropagation()
        setEditingTournament(t)
        setForm({ name: t.name, description: t.description || '', board_size: t.board_size, max_players: t.max_players, format: t.format || 'knockout' })
        setShowModal(true)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        try {
            if (editingTournament) {
                await editTournament(editingTournament.id, form)
            } else {
                await createTournament(form)
            }
            setShowModal(false)
            setEditingTournament(null)
            load()
        } catch (err) {
            alert(err.response?.data?.detail || 'Error')
        }
    }

    const handleDelete = async (e, t) => {
        e.preventDefault()
        e.stopPropagation()
        if (!confirm(`Delete "${t.name}"? This cannot be undone.`)) return
        try {
            await deleteTournament(t.id)
            load()
        } catch (err) {
            alert(err.response?.data?.detail || 'Error')
        }
    }

    const statusBadge = (status) => {
        const classes = { upcoming: 'badge-upcoming', active: 'badge-active', completed: 'badge-completed' }
        return <span className={classes[status] || 'badge-upcoming'}>{status}</span>
    }

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Tournaments</h1>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Manage and compete in Pah-Tum tournaments</p>
                </div>
                <button onClick={openCreate} className="btn-primary flex items-center gap-2">
                    <HiOutlinePlus className="w-4 h-4" /> New Tournament
                </button>
            </div>

            {loading ? (
                <div className="text-center py-20">
                    <div className="inline-block w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
                </div>
            ) : tournaments.length === 0 ? (
                <div className="card p-12 text-center">
                    <HiOutlineTrophy className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No Tournaments Yet</h3>
                    <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>Create your first tournament!</p>
                    <button onClick={openCreate} className="btn-primary">Create Tournament</button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {tournaments.map(t => (
                        <Link key={t.id} to={`/tournaments/${t.id}`} className="card p-5 group relative">
                            {/* Edit/Delete on hover */}
                            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                                <button onClick={(e) => openEdit(e, t)} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors" title="Edit">
                                    <HiOutlinePencil className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                </button>
                                <button onClick={(e) => handleDelete(e, t)} className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors" title="Delete">
                                    <HiOutlineTrash className="w-3.5 h-3.5" style={{ color: '#ef4444' }} />
                                </button>
                            </div>
                            <div className="flex items-start justify-between mb-3">
                                <div className="p-2 rounded-lg" style={{ background: 'rgba(245,158,11,0.1)' }}>
                                    <HiOutlineTrophy className="w-5 h-5 text-gold-500" />
                                </div>
                                {statusBadge(t.status)}
                            </div>
                            <h3 className="text-base font-bold mb-1 group-hover:text-primary-400 transition-colors" style={{ color: 'var(--text-primary)' }}>
                                {t.name}
                            </h3>
                            <p className="text-xs mb-3 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                                {t.description || 'No description'}
                            </p>
                            <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                                <span>{t.format === 'group_stage' ? '🏟️ Group Stage' : '🥊 Knockout'}</span>
                                <span>🎮 {t.board_size}×{t.board_size} board</span>
                                <span>👥 {t.player_count}/{t.max_players}</span>
                            </div>
                        </Link>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
                    <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
                        <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                            {editingTournament ? 'Edit Tournament' : 'Create Tournament'}
                        </h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {!editingTournament && (
                                <div>
                                    <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Format</label>
                                    <div className="flex gap-2">
                                        {[['knockout', '🥊 Knockout'], ['group_stage', '🏟️ Group Stage']].map(([val, label]) => (
                                            <button key={val} type="button" onClick={() => setForm({ ...form, format: val })}
                                                className="flex-1 py-2.5 rounded-lg text-xs font-bold transition-all"
                                                style={{
                                                    background: form.format === val ? 'linear-gradient(135deg, #3b82f6, #2563eb)' : 'var(--bg-secondary)',
                                                    color: form.format === val ? 'white' : 'var(--text-secondary)',
                                                }}>{label}</button>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Tournament Name</label>
                                <input className="input-field" placeholder="e.g. Pah-Tum Championship 2026" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Description</label>
                                <textarea className="input-field h-20 resize-none" placeholder="Tournament description..." value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Board Size</label>
                                    <select className="input-field" value={form.board_size} onChange={e => setForm({ ...form, board_size: parseInt(e.target.value) })}>
                                        {[3, 4, 5, 6, 7, 8, 9, 10].map(n => (<option key={n} value={n}>{n}×{n}</option>))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Max Participants</label>
                                    <select className="input-field" value={form.max_players} onChange={e => setForm({ ...form, max_players: parseInt(e.target.value) })}>
                                        {[4, 8, 16, 32, 64].map(n => (<option key={n} value={n}>{n}</option>))}
                                    </select>
                                </div>
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" className="btn-primary flex-1">{editingTournament ? 'Save' : 'Create'}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
