import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getOverviewStats } from '../api'
import {
    HiOutlineUserGroup,
    HiOutlineTrophy,
    HiOutlinePlayCircle,
    HiOutlineChartBar,
} from 'react-icons/hi2'

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getOverviewStats()
            .then(res => setStats(res.data))
            .catch(() => setStats(null))
            .finally(() => setLoading(false))
    }, [])

    const cards = [
        { label: 'Total Players', value: stats?.total_players || 0, icon: HiOutlineUserGroup, color: '#3b82f6', bg: 'rgba(99,102,241,0.1)' },
        { label: 'Tournaments', value: stats?.total_tournaments || 0, icon: HiOutlineTrophy, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
        { label: 'Matches Played', value: stats?.completed_matches || 0, icon: HiOutlinePlayCircle, color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
        { label: 'Active Tournaments', value: stats?.active_tournaments || 0, icon: HiOutlineChartBar, color: '#ec4899', bg: 'rgba(236,72,153,0.1)' },
    ]

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl md:text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>
                    Dashboard
                </h1>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    Welcome to the Pah-Tum Tournament Center
                </p>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {cards.map(({ label, value, icon: Icon, color, bg }) => (
                    <div key={label} className="stat-card group">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{label}</p>
                                <p className="mt-2 text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>{value}</p>
                            </div>
                            <div className="p-2.5 rounded-xl" style={{ background: bg }}>
                                <Icon className="w-6 h-6" style={{ color }} />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Quick Play */}
                <div className="card p-6">
                    <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Quick Play</h2>
                    <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
                        Jump into a game against the AI or challenge a friend.
                    </p>
                    <Link to="/play" className="btn-primary inline-block">
                        ▶ Start New Game
                    </Link>
                </div>

                {/* Recent Activity */}
                <div className="card p-6">
                    <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Top Players</h2>
                    {stats?.top_players?.length > 0 ? (
                        <div className="space-y-2.5">
                            {stats.top_players.map((p, i) => (
                                <div key={p.id} className="flex items-center gap-3">
                                    <div
                                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                                        style={{
                                            background: i === 0 ? 'linear-gradient(135deg, #fbbf24, #f59e0b)' :
                                                i === 1 ? 'linear-gradient(135deg, #94a3b8, #64748b)' :
                                                    i === 2 ? 'linear-gradient(135deg, #d97706, #92400e)' :
                                                        'var(--bg-secondary)',
                                            color: i > 2 ? 'var(--text-secondary)' : 'white',
                                        }}
                                    >
                                        {i + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{p.name}</p>
                                    </div>
                                    <div className="text-right">
                                        <span className="text-sm font-bold" style={{ color: '#10b981' }}>{p.wins}W</span>
                                        <span className="mx-1 text-xs" style={{ color: 'var(--text-muted)' }}>·</span>
                                        <span className="text-sm font-bold" style={{ color: '#ef4444' }}>{p.losses}L</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No players registered yet. <Link to="/players" className="text-primary-400 hover:underline">Add players</Link></p>
                    )}
                </div>
            </div>

            {/* Recent Matches */}
            <div className="card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Recent Matches</h2>
                    <Link to="/matches" className="text-sm font-semibold text-primary-400 hover:text-primary-300">
                        View All →
                    </Link>
                </div>
                {stats?.recent_matches?.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr style={{ color: 'var(--text-muted)' }}>
                                    <th className="text-left py-2 font-semibold">Match</th>
                                    <th className="text-center py-2 font-semibold">Score</th>
                                    <th className="text-right py-2 font-semibold">Result</th>
                                </tr>
                            </thead>
                            <tbody>
                                {stats.recent_matches.map(m => (
                                    <tr key={m.id} className="border-t" style={{ borderColor: 'var(--border-color)' }}>
                                        <td className="py-3" style={{ color: 'var(--text-primary)' }}>
                                            <span className="font-medium">White vs Black</span>
                                        </td>
                                        <td className="py-3 text-center font-bold" style={{ color: 'var(--text-primary)' }}>
                                            {m.white_score} - {m.black_score}
                                        </td>
                                        <td className="py-3 text-right">
                                            <span className={`badge ${m.winner === 'draw' ? 'badge-upcoming' : 'badge-active'}`}>
                                                {m.winner === 'draw' ? 'Draw' : m.winner === 'white' ? 'White Wins' : 'Black Wins'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No matches played yet. <Link to="/play" className="text-primary-400 hover:underline">Play your first game!</Link></p>
                )}
            </div>

            {/* Game Rules Info */}
            <div className="card p-6" style={{ borderLeft: '3px solid #3b82f6' }}>
                <h2 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>📖 About Pah-Tum</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    <ul className="space-y-1.5 list-disc list-inside">
                        <li>Two players alternate placing stones (White first, then Black)</li>
                        <li>Board size: configurable N×N (default 7×7)</li>
                        <li>Only horizontal &amp; vertical lines count — no diagonals</li>
                    </ul>
                    <ul className="space-y-1.5 list-disc list-inside">
                        <li>Runs of 3+ stones score points (longer = more points)</li>
                        <li>Game ends when the board is full</li>
                        <li>Highest total score wins!</li>
                    </ul>
                </div>
            </div>
        </div>
    )
}
