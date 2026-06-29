import { useState, useEffect } from 'react'
import { getBots, createBot, updateBot, testBot, deleteBot, uploadLocalBot } from '../api'
import { HiOutlineCpuChip, HiOutlinePlus, HiOutlineTrash, HiOutlineSignal, HiOutlinePencil } from 'react-icons/hi2'

export default function Bots() {
    const [bots, setBots] = useState([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [editingBot, setEditingBot] = useState(null)
    const [form, setForm] = useState({ name: '', api_url: '', owner: '', description: '' })
    const [localForm, setLocalForm] = useState({ name: '', owner: '', description: '', entry_function: 'bot_move', file: null })
    const [testResults, setTestResults] = useState({})
    const [testing, setTesting] = useState({})

    const load = () => {
        getBots().then(r => setBots(r.data)).catch(() => { }).finally(() => setLoading(false))
    }
    useEffect(load, [])

    const openCreate = () => {
        setEditingBot(null)
        setForm({ name: '', api_url: '', owner: '', description: '' })
        setShowModal(true)
    }

    const openEdit = (bot) => {
        setEditingBot(bot)
        setForm({ name: bot.name, api_url: bot.api_url, owner: bot.owner || '', description: bot.description || '' })
        setShowModal(true)
    }

    const handleSubmit = async () => {
        if (!form.name || !form.api_url) return alert('Name and API URL are required')
        try {
            if (editingBot) {
                await updateBot(editingBot.id, form)
            } else {
                await createBot(form)
            }
            setForm({ name: '', api_url: '', owner: '', description: '' })
            setShowModal(false)
            setEditingBot(null)
            load()
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed')
        }
    }

    const handleLocalUpload = async () => {
        if (!localForm.name || !localForm.file) {
            return alert('Bot name and Python file are required')
        }
        const fd = new FormData()
        fd.append('name', localForm.name)
        fd.append('owner', localForm.owner)
        fd.append('description', localForm.description)
        fd.append('entry_function', localForm.entry_function || 'bot_move')
        fd.append('file', localForm.file)
        try {
            await uploadLocalBot(fd)
            setLocalForm({ name: '', owner: '', description: '', entry_function: 'bot_move', file: null })
            load()
            alert('Local Python bot uploaded and registered.')
        } catch (err) {
            alert(err.response?.data?.detail || 'Upload failed')
        }
    }

    const handleTest = async (id) => {
        setTesting(p => ({ ...p, [id]: true }))
        try {
            const res = await testBot(id)
            setTestResults(p => ({ ...p, [id]: res.data }))
            load()
        } catch (err) {
            setTestResults(p => ({ ...p, [id]: { success: false, message: 'Request failed' } }))
        } finally {
            setTesting(p => ({ ...p, [id]: false }))
        }
    }

    const handleDelete = async (id) => {
        if (!confirm('Delete this bot?')) return
        try { await deleteBot(id); load() } catch { alert('Failed to delete bot') }
    }

    const statusColors = {
        online: '#10b981', offline: '#ef4444', timeout: '#f59e0b', error: '#ef4444', registered: '#3b82f6',
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>API Bots</h1>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Register bots as HTTP APIs or upload Python code directly</p>
                </div>
                <button onClick={openCreate} className="btn-primary flex items-center gap-2">
                    <HiOutlinePlus className="w-4 h-4" /> Register Bot
                </button>
            </div>

            {/* API Contract Info */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* HTTP API Bots */}
                <div className="card p-5" style={{ borderColor: '#3b82f6', borderWidth: '1px' }}>
                    <h3 className="text-sm font-bold mb-2 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <HiOutlineCpuChip className="w-5 h-5" style={{ color: '#3b82f6' }} /> HTTP Bot API Contract
                    </h3>
                    <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
                        Option 1: Host your own HTTP server that accepts POST requests with the game state and responds with a move.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="rounded-lg p-3" style={{ background: 'var(--bg-secondary)' }}>
                            <p className="text-[10px] font-bold mb-1" style={{ color: '#10b981' }}>REQUEST (POST to your URL)</p>
                            <pre className="text-[10px] overflow-x-auto" style={{ color: 'var(--text-secondary)' }}>{`{
  "board": [[".", "W", ...], ...],
  "board_size": 7,
  "your_stone": "W" or "B",
  "your_score": 5,
  "opponent_score": 3
}`}</pre>
                        </div>
                        <div className="rounded-lg p-3" style={{ background: 'var(--bg-secondary)' }}>
                            <p className="text-[10px] font-bold mb-1" style={{ color: '#f59e0b' }}>RESPONSE (JSON)</p>
                            <pre className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{`{ "row": 3, "col": 4 }`}</pre>
                            <p className="text-[10px] mt-2" style={{ color: 'var(--text-muted)' }}>
                                ⏱ Timeout: 5s • Invalid → random fallback
                            </p>
                        </div>
                    </div>
                </div>

                {/* Upload Local Python Bot */}
                <div className="card p-5" style={{ borderColor: '#10b981', borderWidth: '1px' }}>
                    <h3 className="text-sm font-bold mb-2 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <HiOutlineCpuChip className="w-5 h-5" style={{ color: '#10b981' }} /> Upload Python Bot (Recommended)
                    </h3>
                    <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
                        Option 2: Upload a single <code>.py</code> file that defines
                        <code> bot_move(game_state: dict) -&gt; {"{ row, col }"}</code>.
                        The tournament server will import and run it for you.
                    </p>
                    <div className="space-y-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Bot Name *</label>
                                <input
                                    className="input-field"
                                    value={localForm.name}
                                    onChange={e => setLocalForm(f => ({ ...f, name: e.target.value }))}
                                    placeholder="Team 1 – Algo 1"
                                />
                            </div>
                            <div>
                                <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Owner / Team</label>
                                <input
                                    className="input-field"
                                    value={localForm.owner}
                                    onChange={e => setLocalForm(f => ({ ...f, owner: e.target.value }))}
                                    placeholder="Team 1"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Description</label>
                            <input
                                className="input-field"
                                value={localForm.description}
                                onChange={e => setLocalForm(f => ({ ...f, description: e.target.value }))}
                                placeholder="Brief strategy description"
                            />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-end">
                            <div>
                                <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Python File (*.py) *</label>
                                <input
                                    type="file"
                                    accept=".py"
                                    className="block w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary-500 file:text-white hover:file:bg-primary-600"
                                    onChange={e => setLocalForm(f => ({ ...f, file: e.target.files?.[0] || null }))}
                                />
                            </div>
                            <div>
                                <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Entry Function</label>
                                <input
                                    className="input-field"
                                    value={localForm.entry_function}
                                    onChange={e => setLocalForm(f => ({ ...f, entry_function: e.target.value }))}
                                    placeholder="bot_move"
                                />
                            </div>
                        </div>
                        <button onClick={handleLocalUpload} className="btn-gold w-full text-xs mt-1">
                            Upload & Register Python Bot
                        </button>
                        <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
                            Your file will be stored securely on the server and used only for this tournament.
                        </p>
                    </div>
                </div>
            </div>

            {/* Bot List */}
            {loading ? (
                <div className="text-center py-16"><div className="inline-block w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : bots.length === 0 ? (
                <div className="card p-12 text-center">
                    <HiOutlineCpuChip className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No Bots Registered</h3>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Register your first API bot!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {bots.map(bot => (
                        <div key={bot.id} className="card p-4">
                            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style={{
                                        background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: 'white',
                                    }}>🤖</div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-0.5">
                                            <h3 className="text-sm font-bold truncate" style={{ color: 'var(--text-primary)' }}>{bot.name}</h3>
                                            <span className="shrink-0 inline-block w-2 h-2 rounded-full" style={{ background: statusColors[bot.status] || '#3b82f6' }} />
                                            <span className="text-[10px] font-semibold shrink-0" style={{ color: statusColors[bot.status] || '#3b82f6' }}>{bot.status}</span>
                                        </div>
                                        <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{bot.api_url}</p>
                                        {bot.owner && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>by {bot.owner}</p>}
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="flex gap-3 text-center">
                                        {[['W', bot.wins, '#10b981'], ['L', bot.losses, '#ef4444'], ['D', bot.draws, '#3b82f6']].map(([l, v, c]) => (
                                            <div key={l}>
                                                <div className="text-sm font-bold" style={{ color: c }}>{v}</div>
                                                <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{l}</div>
                                            </div>
                                        ))}
                                    </div>
                                    <button onClick={() => handleTest(bot.id)} disabled={testing[bot.id]} className="btn-secondary text-xs flex items-center gap-1">
                                        {testing[bot.id] ? <span className="inline-block w-3.5 h-3.5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" /> : <HiOutlineSignal className="w-3.5 h-3.5" />}
                                        Test
                                    </button>
                                    <button onClick={() => openEdit(bot)} className="p-2 rounded-lg hover:bg-white/10 transition-colors" title="Edit">
                                        <HiOutlinePencil className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                                    </button>
                                    <button onClick={() => handleDelete(bot.id)} className="p-2 rounded-lg hover:bg-red-500/10 transition-colors" title="Delete">
                                        <HiOutlineTrash className="w-4 h-4" style={{ color: '#ef4444' }} />
                                    </button>
                                </div>
                            </div>
                            {testResults[bot.id] && (
                                <div className="mt-3 p-2.5 rounded-lg text-xs" style={{
                                    background: testResults[bot.id].success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                                    color: testResults[bot.id].success ? '#10b981' : '#ef4444',
                                }}>
                                    {testResults[bot.id].success ? '✓' : '✗'} {testResults[bot.id].message}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Register/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowModal(false)}>
                    <div className="card p-6 w-full max-w-md mx-4 space-y-4" onClick={e => e.stopPropagation()}>
                        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                            {editingBot ? 'Edit Bot' : 'Register New Bot'}
                        </h2>
                        <div>
                            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Bot Name *</label>
                            <input className="input-field" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="My Smart Bot" />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>API URL *</label>
                            <input className="input-field" value={form.api_url} onChange={e => setForm(f => ({ ...f, api_url: e.target.value }))} placeholder="http://localhost:5000/move" />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Owner</label>
                            <input className="input-field" value={form.owner} onChange={e => setForm(f => ({ ...f, owner: e.target.value }))} placeholder="Your name" />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Description</label>
                            <input className="input-field" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Strategy description" />
                        </div>
                        <div className="flex gap-3 pt-2">
                            <button onClick={handleSubmit} className="btn-primary flex-1">{editingBot ? 'Save' : 'Register'}</button>
                            <button onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
