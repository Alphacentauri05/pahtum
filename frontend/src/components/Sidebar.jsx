import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
    LayoutDashboard, Trophy, Users, Bot, 
    Swords, LogOut, Code2, ShieldAlert
} from 'lucide-react';

const links = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/tournaments', icon: Trophy, label: 'Tournaments' },
    { to: '/play', icon: Swords, label: 'Testing Arena' },
    { to: '/leaderboard', icon: Users, label: 'Leaderboard' },
    { to: '/bots', icon: Bot, label: 'My Bots' },
];

export default function Sidebar({ open, onClose }) {
    const { logout, user } = useAuth();

    return (
        <>
            {open && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
                    onClick={onClose}
                />
            )}

            <aside
                className={`
                    fixed top-0 left-0 z-50 h-full w-[260px] flex flex-col
                    transition-transform duration-300 ease-in-out
                    lg:translate-x-0 lg:static lg:z-auto
                    bg-black/40 backdrop-blur-xl border-r border-white/10
                    ${open ? 'translate-x-0' : '-translate-x-full'}
                `}
            >
                {/* Logo */}
                <div className="flex items-center px-6 h-20 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg bg-gradient-to-br from-primary to-purple-600">
                            <Code2 size={24} />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-white tracking-wide">Pah-Tum AI</h1>
                            <p className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase">Arena</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
                    {links.map(({ to, icon: Icon, label }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={to === '/'}
                            onClick={onClose}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                                    isActive 
                                    ? 'bg-primary/20 text-primary border border-primary/30 shadow-[inset_0_0_20px_rgba(100,50,200,0.1)]' 
                                    : 'text-white/60 hover:text-white hover:bg-white/5'
                                }`
                            }
                        >
                            <Icon size={20} />
                            <span className="font-medium">{label}</span>
                        </NavLink>
                    ))}

                    {user?.role === 'ADMIN' && (
                        <div className="pt-6 mt-6 border-t border-white/10">
                            <p className="px-4 mb-2 text-[10px] font-bold tracking-widest text-red-400 uppercase">Admin Console</p>
                            <NavLink
                                to="/admin"
                                onClick={onClose}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                                        isActive 
                                        ? 'bg-red-500/20 text-red-400 border border-red-500/30' 
                                        : 'text-white/60 hover:text-red-400 hover:bg-red-500/10'
                                    }`
                                }
                            >
                                <ShieldAlert size={20} />
                                <span className="font-medium">Platform Admin</span>
                            </NavLink>
                        </div>
                    )}
                </nav>

                {/* User Profile & Logout */}
                <div className="p-4 border-t border-white/10">
                    <button
                        onClick={logout}
                        className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl text-white/70 hover:text-white hover:bg-red-500/20 hover:border-red-500/30 border border-transparent transition-all"
                    >
                        <LogOut size={18} />
                        <span className="font-medium">Sign Out</span>
                    </button>
                </div>
            </aside>
        </>
    );
}
