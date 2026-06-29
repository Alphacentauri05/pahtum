import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { HiOutlineBars3 } from 'react-icons/hi2'

export default function Layout() {
    const [sidebarOpen, setSidebarOpen] = useState(false)

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Mobile topbar */}
                <header
                    className="lg:hidden flex items-center h-14 px-4 border-b"
                    style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
                >
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                        <HiOutlineBars3 className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
                    </button>
                    <div className="ml-3 flex items-center gap-2">
                        <div className="w-7 h-7 rounded-md flex items-center justify-center text-white font-bold text-xs"
                            style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)' }}>
                            PT
                        </div>
                        <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>Pah-Tum</span>
                    </div>
                </header>

                {/* Main content */}
                <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8" style={{ background: 'var(--bg-primary)' }}>
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
