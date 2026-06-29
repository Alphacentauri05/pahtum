import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import {
    HiOutlineHome,
    HiOutlineTrophy,
    HiOutlineUserGroup,
    HiOutlinePlayCircle,
    HiOutlineChartBar,
    HiOutlineClipboardDocumentList,
    HiOutlineCpuChip,
    HiOutlineSun,
    HiOutlineMoon,
    HiOutlineXMark,
} from 'react-icons/hi2'

const links = [
    { to: '/', icon: HiOutlineHome, label: 'Dashboard' },
    { to: '/tournaments', icon: HiOutlineTrophy, label: 'Tournaments' },
    { to: '/play', icon: HiOutlinePlayCircle, label: 'Play Game' },
    { to: '/leaderboard', icon: HiOutlineChartBar, label: 'Leaderboard' },
    { to: '/players', icon: HiOutlineUserGroup, label: 'Players' },
    { to: '/bots', icon: HiOutlineCpuChip, label: 'Bots' },
    { to: '/matches', icon: HiOutlineClipboardDocumentList, label: 'Match History' },
]

export default function Sidebar({ open, onClose }) {
    const { dark, toggle } = useTheme()
    const location = useLocation()

    return (
        <>
            {/* Mobile overlay */}
            {open && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={onClose}
                />
            )}

            <aside
                className={`
          fixed top-0 left-0 z-50 h-full w-[260px] flex flex-col
          transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
                style={{
                    background: 'var(--bg-sidebar)',
                    borderRight: '1px solid var(--border-color)',
                }}
            >
                {/* Logo */}
                <div className="flex items-center justify-between px-5 h-16 border-b" style={{ borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-black text-sm"
                            style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)' }}>
                            PT
                        </div>
                        <div>
                            <h1 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Pah-Tum</h1>
                            <p className="text-[10px] font-semibold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>TOURNAMENT</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="lg:hidden p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
                        <HiOutlineXMark className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                    <p className="px-4 py-2 text-[10px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                        Main Menu
                    </p>
                    {links.map(({ to, icon: Icon, label }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={to === '/'}
                            onClick={onClose}
                            className={({ isActive }) =>
                                `sidebar-link ${isActive ? 'active' : ''}`
                            }
                        >
                            <Icon className="w-5 h-5 flex-shrink-0" />
                            <span>{label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Theme toggle */}
                <div className="p-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    <button
                        onClick={toggle}
                        className="sidebar-link w-full"
                    >
                        {dark ? <HiOutlineSun className="w-5 h-5" /> : <HiOutlineMoon className="w-5 h-5" />}
                        <span>{dark ? 'Light Mode' : 'Dark Mode'}</span>
                    </button>
                </div>
            </aside>
        </>
    )
}
