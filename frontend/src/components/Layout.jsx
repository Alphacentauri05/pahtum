import React, { useState, useEffect } from 'react';
import { NavLink, Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
    LayoutDashboard, Trophy, Users, Bot, 
    Swords, LogOut, ShieldAlert, Menu, X, Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const navLinks = [
    { to: '/', icon: LayoutDashboard, label: 'Overview', public: true },
    { to: '/tournaments', icon: Trophy, label: 'Tournaments', public: true },
    { to: '/play', icon: Swords, label: 'Arena', public: false },
    { to: '/leaderboard', icon: Users, label: 'Rankings', public: true },
    { to: '/bots', icon: Bot, label: 'My Agents', public: false },
];

export default function Layout() {
    const { user, logout } = useAuth();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();

    // Close mobile menu on route change
    useEffect(() => {
        setMobileMenuOpen(false);
    }, [location]);

    return (
        <div className="min-h-screen flex flex-col relative z-0">
            {/* Floating Top Navbar */}
            <header className="sticky top-4 z-50 mx-4 sm:mx-6 lg:mx-8 mt-4">
                <div className="glass-panel rounded-full px-4 sm:px-6 h-16 flex items-center justify-between shadow-[0_8px_32px_rgba(0,0,0,0.3)] border-white/10 bg-black/40">
                    
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-3 shrink-0 group">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center text-white bg-gradient-to-br from-purple-600 to-pink-600 shadow-[0_0_20px_rgba(168,85,247,0.4)] group-hover:shadow-[0_0_30px_rgba(168,85,247,0.6)] transition-all duration-300">
                            <Sparkles size={20} className="text-white" />
                        </div>
                        <div className="hidden sm:block">
                            <h1 className="text-lg font-extrabold text-white tracking-tight leading-none">Pah-Tum</h1>
                            <p className="text-[10px] font-bold tracking-[0.2em] text-pink-400 uppercase leading-tight mt-0.5">Arena</p>
                        </div>
                    </Link>

                    {/* Desktop Navigation */}
                    <nav className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-full border border-white/5">
                        {navLinks.filter(l => l.public || user).map(({ to, icon: Icon, label }) => (
                            <NavLink
                                key={to}
                                to={to}
                                end={to === '/'}
                                className={({ isActive }) =>
                                    `nav-pill ${isActive ? 'nav-pill-active' : 'nav-pill-inactive'}`
                                }
                            >
                                <Icon size={16} />
                                <span>{label}</span>
                            </NavLink>
                        ))}
                        
                        {user?.role === 'ADMIN' && (
                            <NavLink to="/admin" className={({ isActive }) => `nav-pill ${isActive ? 'bg-red-500/20 text-red-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]' : 'text-white/50 hover:text-red-400 hover:bg-white/5'}`}>
                                <ShieldAlert size={16} />
                                <span>Admin</span>
                            </NavLink>
                        )}
                    </nav>

                    {/* Right side - Auth / User Profile */}
                    <div className="hidden md:flex items-center gap-4 shrink-0">
                        {user ? (
                            <div className="flex items-center gap-4 pl-4 border-l border-white/10">
                                <div className="text-right">
                                    <p className="text-sm font-bold text-white leading-tight">{user.username}</p>
                                    <p className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider">{user.role}</p>
                                </div>
                                <button
                                    onClick={logout}
                                    className="w-10 h-10 rounded-full flex items-center justify-center text-white/50 hover:text-white hover:bg-red-500/20 transition-all duration-300"
                                    title="Sign Out"
                                >
                                    <LogOut size={18} />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3">
                                <Link to="/login" className="text-sm font-bold text-white/70 hover:text-white px-4 py-2 transition-colors">
                                    Sign In
                                </Link>
                                <Link to="/signup" className="glass-button glass-button-primary !py-2 !px-5 !rounded-full !text-sm">
                                    Get Started
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Mobile menu button */}
                    <div className="flex items-center md:hidden shrink-0">
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="p-2 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                        >
                            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>
                </div>

                {/* Mobile menu dropdown */}
                <AnimatePresence>
                    {mobileMenuOpen && (
                        <motion.div 
                            initial={{ opacity: 0, y: -20, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -20, scale: 0.95 }}
                            transition={{ duration: 0.2 }}
                            className="absolute top-20 left-0 right-0 glass-panel p-4 shadow-2xl mx-0"
                        >
                            <div className="space-y-2">
                                {navLinks.filter(l => l.public || user).map(({ to, icon: Icon, label }) => (
                                    <NavLink
                                        key={to}
                                        to={to}
                                        end={to === '/'}
                                        className={({ isActive }) =>
                                            `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold ${
                                                isActive ? 'bg-white/10 text-white' : 'text-white/60 hover:bg-white/5 hover:text-white'
                                            }`
                                        }
                                    >
                                        <Icon size={18} /> {label}
                                    </NavLink>
                                ))}
                            </div>
                            
                            <div className="border-t border-white/10 mt-4 pt-4">
                                {user ? (
                                    <div className="space-y-4">
                                        <div className="px-4">
                                            <p className="text-sm font-bold text-white">{user.username}</p>
                                            <p className="text-xs text-purple-400 font-semibold">{user.role}</p>
                                        </div>
                                        <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-400 hover:bg-red-500/10 font-bold">
                                            <LogOut size={18} /> Sign Out
                                        </button>
                                    </div>
                                ) : (
                                    <div className="flex flex-col gap-3">
                                        <Link to="/login" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 text-white font-bold hover:bg-white/10">
                                            Sign In
                                        </Link>
                                        <Link to="/signup" className="glass-button glass-button-primary w-full">
                                            Get Started
                                        </Link>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </header>

            {/* Main content */}
            <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12 relative z-10">
                <Outlet />
            </main>
        </div>
    );
}
