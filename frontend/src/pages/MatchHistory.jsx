import { useState, useEffect } from 'react'
import { getMatches } from '../api'
import { HiOutlineClipboardDocumentList } from 'react-icons/hi2'

export default function MatchHistory() {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getMatches().then(r => setMatches(r.data)).catch(() => { }).finally(() => setLoading(false))
    }, [])

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Match History</h1>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>All completed and scheduled matches</p>
            </div>

            {loading ? (
                <div className="text-center py-20"><div className="inline-block w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : matches.length === 0 ? (
                <div className="card p-12 text-center">
                    <HiOutlineClipboardDocumentList className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No Matches Yet</h3>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Play some games to see match history here!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {matches.map(m => (
                        <div key={m.id} className="card p-4">
                            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`badge ${m.status === 'completed' ? 'badge-completed' : m.status === 'scheduled' ? 'badge-upcoming' : 'badge-active'}`}>
                                            {m.status}
                                        </span>
                                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                            {m.board_size}×{m.board_size}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-primary)' }}>
                                        <span className="font-semibold">{m.player_white_name || 'White'}</span>
                                        <span style={{ color: 'var(--text-muted)' }}>vs</span>
                                        <span className="font-semibold">{m.player_black_name || 'Black'}</span>
                                    </div>
                                </div>
                                {m.status === 'completed' && (
                                    <div className="flex items-center gap-4">
                                        <div className="text-center">
                                            <div className="text-xl font-extrabold" style={{ color: 'var(--text-primary)' }}>
                                                {m.white_score} - {m.black_score}
                                            </div>
                                        </div>
                                        <span className={`badge ${m.winner === 'draw' ? 'badge-upcoming' : 'badge-active'}`}>
                                            {m.winner === 'draw' ? 'Draw' : m.winner === 'white' ? 'White Wins' : 'Black Wins'}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
