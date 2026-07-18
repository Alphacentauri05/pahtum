import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tournaments from './pages/Tournaments'
import TournamentDetail from './pages/TournamentDetail'
import Players from './pages/Players'
import PlayGame from './pages/PlayGame'
import Leaderboard from './pages/Leaderboard'
import MatchHistory from './pages/MatchHistory'
import Bots from './pages/Bots'
import Login from './pages/Login'
import Signup from './pages/Signup'
import AdminDashboard from './pages/AdminDashboard'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
    return (
        <Routes>
            {/* The Layout encapsulates everything now so the Navbar is always visible */}
            <Route element={<Layout />}>
                
                {/* Public Routes */}
                <Route path="/" element={<Dashboard />} />
                <Route path="/tournaments" element={<Tournaments />} />
                <Route path="/tournaments/:id" element={<TournamentDetail />} />
                <Route path="/leaderboard" element={<Leaderboard />} />
                <Route path="/players" element={<Players />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                
                {/* Protected Routes */}
                <Route element={<ProtectedRoute />}>
                    <Route path="/play" element={<PlayGame />} />
                    <Route path="/bots" element={<Bots />} />
                    <Route path="/matches" element={<MatchHistory />} />
                    
                    {/* Admin Only Route */}
                    <Route element={<ProtectedRoute requireAdmin={true} />}>
                        <Route path="/admin" element={<AdminDashboard />} />
                    </Route>
                </Route>
                
            </Route>
        </Routes>
    )
}
