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

export default function App() {
    return (
        <Routes>
            <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/tournaments" element={<Tournaments />} />
                <Route path="/tournaments/:id" element={<TournamentDetail />} />
                <Route path="/players" element={<Players />} />
                <Route path="/play" element={<PlayGame />} />
                <Route path="/leaderboard" element={<Leaderboard />} />
                <Route path="/bots" element={<Bots />} />
                <Route path="/matches" element={<MatchHistory />} />
            </Route>
        </Routes>
    )
}
