import React, { useState, useEffect } from 'react';
import api from '../api';
import { Users, Trash2, ShieldAlert } from 'lucide-react';

export default function AdminDashboard() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadUsers = () => {
        api.get('/players')
            .then(res => setUsers(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadUsers();
    }, []);

    const handleDelete = async (uid) => {
        if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
        try {
            await api.delete(`/players/${uid}`);
            loadUsers();
        } catch (err) {
            alert('Failed to delete user: ' + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8 animate-in">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-red-500/20 text-red-500 flex items-center justify-center">
                    <ShieldAlert size={28} />
                </div>
                <div>
                    <h1 className="text-3xl font-extrabold text-white">Admin Console</h1>
                    <p className="mt-1 text-white/60">Manage users and platform settings</p>
                </div>
            </div>

            <div className="glass-panel p-6">
                <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    <Users className="text-primary" /> Registered Users
                </h2>
                
                {loading ? (
                    <div className="flex justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/10 text-white/60 text-sm">
                                    <th className="pb-3 px-4 font-semibold">User</th>
                                    <th className="pb-3 px-4 font-semibold">Email</th>
                                    <th className="pb-3 px-4 font-semibold">Role</th>
                                    <th className="pb-3 px-4 font-semibold">Joined</th>
                                    <th className="pb-3 px-4 font-semibold text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(u => (
                                    <tr key={u.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                        <td className="py-4 px-4 font-semibold text-white">
                                            {u.username}
                                        </td>
                                        <td className="py-4 px-4 text-white/70">{u.email}</td>
                                        <td className="py-4 px-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${u.role === 'ADMIN' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                                {u.role}
                                            </span>
                                        </td>
                                        <td className="py-4 px-4 text-white/70 text-sm">
                                            {new Date(u.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="py-4 px-4 text-right">
                                            {u.role !== 'ADMIN' && (
                                                <button 
                                                    onClick={() => handleDelete(u.id)}
                                                    className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
