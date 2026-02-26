'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getCompanies, CompanyRecord } from '@/services/apiClient';
import { Building2, Truck, Activity, RefreshCw, ChevronRight, MapPin, Search } from 'lucide-react';
import styles from './page.module.css';

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 120, damping: 18 } } };

export default function AdminDashboard() {
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();

    const [companies, setCompanies] = useState<CompanyRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [search, setSearch] = useState('');

    const fetchAll = useCallback(async (silent = false) => {
        if (!silent) setLoading(true);
        else setRefreshing(true);
        const data = await getCompanies();
        setCompanies(data);
        setLoading(false);
        setRefreshing(false);
    }, []);

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
                <AnimatePresence>
                    <motion.div variants={fadeUp} initial="hidden" animate="show" className={styles.tableSection}>
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
                </AnimatePresence>
            )}
        </div>
    );
}
