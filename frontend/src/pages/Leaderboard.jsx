import { useState, useEffect } from 'react'
import { getLeaderboard } from '../api'
import { HiOutlineTrophy } from 'react-icons/hi2'

export default function Leaderboard() {
    const [players, setPlayers] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getLeaderboard().then(r => setPlayers(r.data)).catch(() => { }).finally(() => setLoading(false))
    }, [])

    const medals = ['🥇', '🥈', '🥉']

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Leaderboard</h1>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Top Pah-Tum players ranked by wins</p>
            </div>

            {loading ? (
                <div className="text-center py-20"><div className="inline-block w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : players.length === 0 ? (
                <div className="card p-12 text-center">
                    <HiOutlineTrophy className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No Rankings Yet</h3>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Play some matches to see the leaderboard!</p>
                </div>
            ) : (
                <>
                    {/* Top 3 podium */}
                    {players.length >= 3 && (
                        <div className="grid grid-cols-3 gap-3">
                            {[players[1], players[0], players[2]].map((p, idx) => {
                                const rank = idx === 0 ? 2 : idx === 1 ? 1 : 3
                                const height = rank === 1 ? 'h-32' : rank === 2 ? 'h-24' : 'h-20'
                                return (
                                    <div key={p.id} className={`card p-4 text-center flex flex-col items-center justify-end ${rank === 1 ? 'order-2' : rank === 2 ? 'order-1' : 'order-3'}`}>
                                        <div className="text-3xl mb-2">{medals[rank - 1]}</div>
                                        <div className="w-12 h-12 rounded-full flex items-center justify-center text-white text-lg font-bold mb-2" style={{ background: p.avatar_color }}>
                                            {p.name.charAt(0).toUpperCase()}
                                        </div>
                                        <h3 className="text-sm font-bold truncate w-full" style={{ color: 'var(--text-primary)' }}>{p.name}</h3>
                                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{p.wins} wins • {p.total_score} pts</p>
                                        <div className={`w-full mt-2 rounded-t-lg ${height}`} style={{
                                            background: rank === 1 ? 'linear-gradient(to top, rgba(245,158,11,0.2), rgba(245,158,11,0.05))' :
                                                rank === 2 ? 'linear-gradient(to top, rgba(148,163,184,0.2), rgba(148,163,184,0.05))' :
                                                    'linear-gradient(to top, rgba(217,119,6,0.2), rgba(217,119,6,0.05))'
                                        }} />
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Full table */}
                    <div className="card overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                                    <th className="text-left px-4 py-3 font-semibold">#</th>
                                    <th className="text-left px-4 py-3 font-semibold">Player</th>
                                    <th className="text-center px-4 py-3 font-semibold">W</th>
                                    <th className="text-center px-4 py-3 font-semibold">L</th>
                                    <th className="text-center px-4 py-3 font-semibold">D</th>
                                    <th className="text-center px-4 py-3 font-semibold">Played</th>
                                    <th className="text-right px-4 py-3 font-semibold">Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {players.map((p, i) => (
                                    <tr key={p.id} className="border-t transition-colors hover:bg-primary-500/5" style={{ borderColor: 'var(--border-color)' }}>
                                        <td className="px-4 py-3 font-bold" style={{ color: 'var(--text-muted)' }}>
                                            {i < 3 ? medals[i] : i + 1}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ background: p.avatar_color }}>
                                                    {p.name.charAt(0).toUpperCase()}
                                                </div>
                                                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{p.name}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-center font-bold" style={{ color: '#10b981' }}>{p.wins}</td>
                                        <td className="px-4 py-3 text-center font-bold" style={{ color: '#ef4444' }}>{p.losses}</td>
                                        <td className="px-4 py-3 text-center font-bold" style={{ color: '#3b82f6' }}>{p.draws}</td>
                                        <td className="px-4 py-3 text-center" style={{ color: 'var(--text-secondary)' }}>{p.matches_played}</td>
                                        <td className="px-4 py-3 text-right font-bold" style={{ color: '#f59e0b' }}>{p.total_score}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}
