'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getCompanies, CompanyRecord, getAdminUsers, AdminUserRecord, patchAdminUser } from '@/services/apiClient';
import { Building2, Truck, Activity, RefreshCw, ChevronRight, MapPin, Search, Users, Shield, Edit2, CheckCircle, XCircle } from 'lucide-react';
import styles from './page.module.css';
import dynamic from 'next/dynamic';

const GoogleMapComponent = dynamic(() => import('@/components/GoogleMapComponent'), { ssr: false });

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 120, damping: 18 } } };

export default function AdminDashboard() {
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();

    const [companies, setCompanies] = useState<CompanyRecord[]>([]);
    const [usersList, setUsersList] = useState<AdminUserRecord[]>([]);
    const [tab, setTab] = useState<'companies' | 'users' | 'map'>('companies');
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [search, setSearch] = useState('');
    const [editingUser, setEditingUser] = useState<number | null>(null);
    const [editRole, setEditRole] = useState('');

    const fetchAll = useCallback(async (silent = false) => {
        if (!silent) setLoading(true);
        else setRefreshing(true);
        const [cData, uData] = await Promise.all([getCompanies(), getAdminUsers()]);
        setCompanies(cData);
        setUsersList(uData);
        setLoading(false);
        setRefreshing(false);
    }, []);

    const handleToggleUserActive = async (user: AdminUserRecord) => {
        const success = await patchAdminUser(user.id, { is_active: !user.is_active });
        if (success) {
            setUsersList(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !user.is_active } : u));
        }
    };

    const handleSaveRole = async (user: AdminUserRecord) => {
        const success = await patchAdminUser(user.id, { role: editRole });
        if (success) {
            setUsersList(prev => prev.map(u => u.id === user.id ? { ...u, role: editRole } : u));
            setEditingUser(null);
        }
    };

    // Auth Guard
    useEffect(() => {
        if (!authLoading) {
            if (!isAuthenticated || user?.role !== 'admin') {
                router.replace('/dashboard');
            } else {
                fetchAll();
            }
        }
    }, [authLoading, isAuthenticated, user, router, fetchAll]);

    if (authLoading || (isAuthenticated && user?.role !== 'admin' && loading)) {
        return (
            <div className={styles.loader}>
                <div className={styles.loaderRing} />
                <span>Verifying credentials...</span>
            </div>
        );
    }

    const filteredCompanies = companies.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        (c.city && c.city.toLowerCase().includes(search.toLowerCase()))
    );

    const filteredUsers = usersList.filter(u =>
        u.username.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()) ||
        u.company_name.toLowerCase().includes(search.toLowerCase())
    );

    const totalActiveTrucks = companies.reduce((acc, c) => acc + c.active_trucks, 0);
    const totalActiveTrips = companies.reduce((acc, c) => acc + c.active_trips, 0);

    return (
        <div className={styles.page}>
            <motion.div variants={stagger} initial="hidden" animate="show" className={styles.header}>
                <motion.div variants={fadeUp} className={styles.headerLeft}>
                    <div className={styles.breadcrumb}><span>Platform</span><ChevronRight size={14} /><span>Admin Control</span></div>
                    <h1 className={styles.title}>Global Registry</h1>
                    <p className={styles.subtitle}>Super-admin view of all onboarded Logistics Companies</p>
                </motion.div>

                <motion.div variants={fadeUp} className={styles.headerRight}>
                    <div style={{ position: 'relative' }}>
                        <input
                            className={styles.searchInput}
                            placeholder="Search companies..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                        <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', right: 12, top: 13 }} />
                    </div>
                    <button className={styles.refreshBtn} onClick={() => fetchAll(true)} disabled={refreshing} title="Refresh records">
                        <RefreshCw size={16} className={refreshing ? styles.spinning : ''} />
                    </button>
                </motion.div>
            </motion.div>

            <motion.div variants={stagger} initial="hidden" animate="show" className={styles.statsGrid}>
                <motion.div variants={fadeUp} className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Building2 size={20} /></div>
                        <span className={styles.statLabel}>Total Tenants</span>
                    </div>
                    <h2 className={styles.statValue}>{companies.length}</h2>
                </motion.div>
                <motion.div variants={fadeUp} className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Users size={20} /></div>
                        <span className={styles.statLabel}>Global System Users</span>
                    </div>
                    <h2 className={styles.statValue}>{usersList.length}</h2>
                </motion.div>
                <motion.div variants={fadeUp} className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Truck size={20} /></div>
                        <span className={styles.statLabel}>Global Active Trucks</span>
                    </div>
                    <h2 className={styles.statValue}>{totalActiveTrucks}</h2>
                </motion.div>
                <motion.div variants={fadeUp} className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Activity size={20} /></div>
                        <span className={styles.statLabel}>Global Active Trips</span>
                    </div>
                    <h2 className={styles.statValue}>{totalActiveTrips}</h2>
                </motion.div>
            </motion.div>

            {loading ? (
                <div className={styles.loader}>
                    <div className={styles.loaderRing} />
                    <span>Loading tenant data...</span>
                </div>
            ) : (
                <>
                    <div className={styles.tabs} style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        {(['companies', 'users', 'map'] as const).map(t => (
                            <button
                                key={t}
                                onClick={() => { setTab(t); setSearch(''); }}
                                style={{
                                    background: 'transparent', color: tab === t ? '#3b82f6' : '#94a3b8',
                                    border: 'none', padding: '0.75rem 1.5rem', cursor: 'pointer',
                                    fontWeight: 600, borderBottom: tab === t ? '2px solid #3b82f6' : '2px solid transparent',
                                    display: 'flex', alignItems: 'center', gap: '8px'
                                }}
                            >
                                {t === 'companies' ? <Building2 size={16} /> : t === 'users' ? <Users size={16} /> : <MapPin size={16} />}
                                {t.charAt(0).toUpperCase() + t.slice(1)}
                            </button>
                        ))}
                    </div>

                    <AnimatePresence mode="wait">
                        {tab === 'companies' && (
                            <motion.div key="companies" variants={fadeUp} initial="hidden" animate="show" exit={{ opacity: 0 }} className={styles.tableSection}>
                                <div className={styles.tableHeader}>
                                    <Building2 className={styles.iconAccent} size={20} />
                                    <h2>Registered Organizations</h2>
                                </div>
                                {filteredCompanies.length === 0 ? (
                                    <div className={styles.empty}>
                                        <Building2 size={48} opacity={0.2} />
                                        <h3>No companies found</h3>
                                        <p>Try adjusting your search query.</p>
                                    </div>
                                ) : (
                                    <div style={{ overflowX: 'auto' }}>
                                        <table className={styles.dataTable}>
                                            <thead>
                                                <tr>
                                                    <th>ORGANIZATION</th>
                                                    <th>STATUS</th>
                                                    <th>LOCATION</th>
                                                    <th>ACTIVE FLEET</th>
                                                    <th>ONBOARDED</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredCompanies.map(c => (
                                                    <tr key={c.company_id}>
                                                        <td>
                                                            <div className={styles.colName}>
                                                                <div className={styles.companyAvatar}>{c.name.substring(0, 2).toUpperCase()}</div>
                                                                {c.name}
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <span className={styles.statusPill} data-active={c.active}>
                                                                {c.active ? 'Active' : 'Suspended'}
                                                            </span>
                                                        </td>
                                                        <td>
                                                            <div className={styles.metric}>
                                                                <MapPin size={14} /> {c.city ? `${c.city}, ${c.country}` : c.country}
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <div className={styles.metricsGroup}>
                                                                <span className={styles.metric}><Truck size={14} /> <strong>{c.active_trucks}</strong> Trucks</span>
                                                                <span className={styles.metric}><Activity size={14} /> <strong>{c.active_trips}</strong> Trips</span>
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <span style={{ color: 'var(--text-muted)' }}>
                                                                {new Date(c.joined_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </motion.div>
                        )}

                        {tab === 'users' && (
                            <motion.div key="users" variants={fadeUp} initial="hidden" animate="show" exit={{ opacity: 0 }} className={styles.tableSection}>
                                <div className={styles.tableHeader}>
                                    <Users className={styles.iconAccent} size={20} />
                                    <h2>System Users</h2>
                                </div>
                                {filteredUsers.length === 0 ? (
                                    <div className={styles.empty}>
                                        <Users size={48} opacity={0.2} />
                                        <h3>No users found</h3>
                                    </div>
                                ) : (
                                    <div style={{ overflowX: 'auto' }}>
                                        <table className={styles.dataTable}>
                                            <thead>
                                                <tr>
                                                    <th>USER</th>
                                                    <th>COMPANY</th>
                                                    <th>ROLE</th>
                                                    <th>STATUS</th>
                                                    <th>ACTIONS</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredUsers.map(u => (
                                                    <tr key={u.id}>
                                                        <td>
                                                            <div className={styles.colName} style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
                                                                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{u.username}</div>
                                                                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{u.email}</div>
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <div className={styles.metric}>
                                                                <Building2 size={14} /> {u.company_name}
                                                            </div>
                                                        </td>
                                                        <td>
                                                            {editingUser === u.id ? (
                                                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                                                    <select
                                                                        value={editRole} onChange={e => setEditRole(e.target.value)}
                                                                        style={{ background: '#0f172a', border: '1px solid #3b82f6', color: 'white', padding: '4px', borderRadius: '4px' }}
                                                                    >
                                                                        <option value="admin">Admin</option>
                                                                        <option value="company_user">Company User</option>
                                                                        <option value="viewer">Viewer</option>
                                                                    </select>
                                                                    <button onClick={() => handleSaveRole(u)} style={{ background: '#10b981', border: 'none', color: 'white', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}>Save</button>
                                                                    <button onClick={() => setEditingUser(null)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>Cancel</button>
                                                                </div>
                                                            ) : (
                                                                <span style={{
                                                                    padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700,
                                                                    background: u.role === 'admin' ? 'rgba(139,92,246,0.1)' : 'rgba(59,130,246,0.1)',
                                                                    color: u.role === 'admin' ? '#c084fc' : '#60a5fa'
                                                                }}>
                                                                    {u.role.toUpperCase()}
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td>
                                                            <button
                                                                onClick={() => handleToggleUserActive(u)}
                                                                className={styles.statusPill}
                                                                data-active={u.is_active}
                                                                style={{ cursor: 'pointer', border: 'none' }}
                                                                title="Click to toggle active status"
                                                            >
                                                                {u.is_active ? 'Active' : 'Disabled'}
                                                            </button>
                                                        </td>
                                                        <td>
                                                            <button
                                                                onClick={() => { setEditingUser(u.id); setEditRole(u.role); }}
                                                                style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: '#cbd5e1', padding: '6px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                                                title="Edit Role"
                                                            >
                                                                <Edit2 size={14} />
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </motion.div>
                        )}

                        {tab === 'map' && (
                            <motion.div key="map" variants={fadeUp} initial="hidden" animate="show" exit={{ opacity: 0 }} className={styles.tableSection}>
                                <div className={styles.tableHeader}>
                                    <MapPin className={styles.iconAccent} size={20} />
                                    <h2>Company HQ Distribution</h2>
                                </div>
                                <div style={{ padding: '0 1rem 1rem 1rem' }}>
                                    <GoogleMapComponent
                                        height="500px"
                                        center={{ lat: 20.5937, lng: 78.9629 }}
                                        zoom={4}
                                        markers={companies.map(c => {
                                            let lat = 20.5937, lng = 78.9629; // default center
                                            const cname = (c.city || c.name).toLowerCase();
                                            if (cname.includes('delhi') || cname.includes('noida') || cname.includes('gurgaon')) { lat = 28.6139; lng = 77.2090; }
                                            else if (cname.includes('mumbai') || cname.includes('thane') || cname.includes('jio')) { lat = 19.0760; lng = 72.8777; }
                                            else if (cname.includes('chennai')) { lat = 13.0827; lng = 80.2707; }
                                            else if (cname.includes('bangalore') || cname.includes('bengaluru')) { lat = 12.9716; lng = 77.5946; }
                                            else if (cname.includes('hyderabad')) { lat = 17.3850; lng = 78.4867; }
                                            else if (cname.includes('pune')) { lat = 18.5204; lng = 73.8567; }
                                            else if (cname.includes('ahmedabad')) { lat = 23.0225; lng = 72.5714; }
                                            else if (cname.includes('kolkata')) { lat = 22.5726; lng = 88.3639; }
                                            else if (cname.includes('surat')) { lat = 21.1702; lng = 72.8311; }

                                            // add slight jitter
                                            lat += (Math.random() - 0.5) * 0.05;
                                            lng += (Math.random() - 0.5) * 0.05;

                                            return {
                                                lat, lng,
                                                title: c.name,
                                                riskLevel: c.active_trucks > 50 ? 'Critical' : (c.active_trucks > 20 ? 'High' : 'Low'),
                                                status: `${c.active_trucks} Active Trucks`,
                                                route: `${c.city || c.country}`
                                            };
                                        })}
                                    />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </>
            )}
        </div>
    );
}
