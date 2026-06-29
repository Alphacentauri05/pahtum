import { useState, useEffect } from 'react'
import { getPlayers, createPlayer, updatePlayer, deletePlayer } from '../api'
import { HiOutlinePlus, HiOutlineUserGroup, HiOutlinePencil, HiOutlineTrash } from 'react-icons/hi2'

const COLORS = ['#3b82f6', '#ec4899', '#10b981', '#f59e0b', '#ef4444', '#60a5fa', '#06b6d4', '#f97316']

export default function Players() {
    const [players, setPlayers] = useState([])
    const [showModal, setShowModal] = useState(false)
    const [editingPlayer, setEditingPlayer] = useState(null)
    const [form, setForm] = useState({ name: '', email: '', avatar_color: COLORS[0] })
    const [search, setSearch] = useState('')
    const [loading, setLoading] = useState(true)

    const load = () => {
        getPlayers().then(r => setPlayers(r.data)).catch(() => { }).finally(() => setLoading(false))
    }
    useEffect(load, [])

    const openCreate = () => {
        setEditingPlayer(null)
        setForm({ name: '', email: '', avatar_color: COLORS[Math.floor(Math.random() * COLORS.length)] })
        setShowModal(true)
    }

    const openEdit = (p) => {
        setEditingPlayer(p)
        setForm({ name: p.name, email: p.email, avatar_color: p.avatar_color })
        setShowModal(true)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        try {
            if (editingPlayer) {
                await updatePlayer(editingPlayer.id, form)
            } else {
                await createPlayer(form)
            }
            setShowModal(false)
            setEditingPlayer(null)
            load()
        } catch (err) { alert(err.response?.data?.detail || 'Error') }
    }

    const handleDelete = async (p) => {
        if (!confirm(`Delete "${p.name}"? This cannot be undone.`)) return
        try {
            await deletePlayer(p.id)
            load()
        } catch (err) { alert(err.response?.data?.detail || 'Error') }
    }

    const filtered = players.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) || p.email.toLowerCase().includes(search.toLowerCase())
    )

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Players</h1>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Manage player registrations</p>
                </div>
                <button onClick={openCreate} className="btn-primary flex items-center gap-2">
                    <HiOutlinePlus className="w-4 h-4" /> Add Player
                </button>
            </div>

            <input className="input-field max-w-sm" placeholder="Search players..." value={search} onChange={e => setSearch(e.target.value)} />

            {loading ? (
                <div className="text-center py-20"><div className="inline-block w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : filtered.length === 0 ? (
                <div className="card p-12 text-center">
                    <HiOutlineUserGroup className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No Players Found</h3>
                    <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>{search ? 'Try different search' : 'Register your first player!'}</p>
                    {!search && <button onClick={openCreate} className="btn-primary">Add Player</button>}
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filtered.map(p => (
                        <div key={p.id} className="card p-5 text-center group relative">
                            {/* Edit/Delete buttons */}
                            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={() => openEdit(p)} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors" title="Edit">
                                    <HiOutlinePencil className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                </button>
                                <button onClick={() => handleDelete(p)} className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors" title="Delete">
                                    <HiOutlineTrash className="w-3.5 h-3.5" style={{ color: '#ef4444' }} />
                                </button>
                            </div>
                            <div className="w-14 h-14 mx-auto rounded-full flex items-center justify-center text-white text-xl font-bold mb-3" style={{ background: p.avatar_color }}>
                                {p.name.charAt(0).toUpperCase()}
                            </div>
                            <h3 className="text-sm font-bold truncate" style={{ color: 'var(--text-primary)' }}>{p.name}</h3>
                            <p className="text-xs truncate mb-3" style={{ color: 'var(--text-muted)' }}>{p.email}</p>
                            <div className="grid grid-cols-3 gap-2">
                                <div className="p-2 rounded-lg" style={{ background: 'rgba(16,185,129,0.1)' }}>
                                    <div className="text-lg font-extrabold" style={{ color: '#10b981' }}>{p.wins}</div>
                                    <div className="text-[10px] font-semibold" style={{ color: 'var(--text-muted)' }}>WINS</div>
                                </div>
                                <div className="p-2 rounded-lg" style={{ background: 'rgba(239,68,68,0.1)' }}>
                                    <div className="text-lg font-extrabold" style={{ color: '#ef4444' }}>{p.losses}</div>
                                    <div className="text-[10px] font-semibold" style={{ color: 'var(--text-muted)' }}>LOSSES</div>
                                </div>
                                <div className="p-2 rounded-lg" style={{ background: 'rgba(99,102,241,0.1)' }}>
                                    <div className="text-lg font-extrabold" style={{ color: '#3b82f6' }}>{p.draws}</div>
                                    <div className="text-[10px] font-semibold" style={{ color: 'var(--text-muted)' }}>DRAWS</div>
                                </div>
                            </div>
                            <div className="mt-3 pt-3 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
                                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{p.matches_played} matches</span>
                                <span className="text-xs font-bold" style={{ color: '#f59e0b' }}>⭐ {p.total_score} pts</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showModal && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
                    <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
                        <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                            {editingPlayer ? 'Edit Player' : 'Add Player'}
                        </h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Name</label>
                                <input className="input-field" placeholder="Player name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Email</label>
                                <input className="input-field" type="email" placeholder="email@example.com" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>Color</label>
                                <div className="flex gap-2">
                                    {COLORS.map(c => (
                                        <button key={c} type="button" onClick={() => setForm({ ...form, avatar_color: c })} className="w-8 h-8 rounded-full transition-transform" style={{ background: c, transform: form.avatar_color === c ? 'scale(1.3)' : 'scale(1)', boxShadow: form.avatar_color === c ? `0 0 0 3px ${c}44` : 'none' }} />
                                    ))}
                                </div>
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" className="btn-primary flex-1">{editingPlayer ? 'Save' : 'Add'}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
