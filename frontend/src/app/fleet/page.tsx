'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
    Truck, User, Package, DollarSign, MapPin, Shield, Activity,
    RefreshCw, ChevronRight, Wifi, AlertTriangle, CheckCircle2, Clock
} from 'lucide-react';
import { getTrucks, getTrips, TruckRecord, TripRecord } from '@/services/apiClient';
import styles from './page.module.css';

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 120, damping: 18 } } };

const RISK_COLOR = (score: number) =>
    score >= 75 ? '#dc2626' : score >= 50 ? '#f59e0b' : score >= 25 ? '#3b82f6' : '#10b981';

const STATUS_STYLE: Record<string, { color: string; bg: string; label: string }> = {
    Alert: { color: '#dc2626', bg: 'rgba(220,38,38,0.1)', label: 'Alert' },
    'In-Transit': { color: '#0ea5e9', bg: 'rgba(14,165,233,0.1)', label: 'In Transit' },
    Scheduled: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', label: 'Scheduled' },
    Completed: { color: '#10b981', bg: 'rgba(16,185,129,0.1)', label: 'Completed' },
    Cancelled: { color: '#6b7280', bg: 'rgba(107,114,128,0.1)', label: 'Cancelled' },
};

type Tab = 'trucks' | 'trips';

export default function FleetPage() {
    const [tab, setTab] = useState<Tab>('trucks');
    const [trucks, setTrucks] = useState<TruckRecord[]>([]);
    const [trips, setTrips] = useState<TripRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('All');

    const fetchAll = useCallback(async (silent = false) => {
        if (!silent) setLoading(true);
        else setRefreshing(true);
        const [t, tr] = await Promise.all([getTrucks(), getTrips()]);
        setTrucks(t);
        setTrips(tr);
        setLoading(false);
        setRefreshing(false);
    }, []);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    const filteredTrucks = trucks.filter(t =>
        t.license_plate?.toLowerCase().includes(search.toLowerCase()) ||
        t.driver_name.toLowerCase().includes(search.toLowerCase()) ||
        t.cargo_type.toLowerCase().includes(search.toLowerCase())
    );

    const tripStatuses = ['All', ...Array.from(new Set(trips.map(t => t.status)))];
    const filteredTrips = trips.filter(t => {
        const matchSearch = t.truck.license_plate?.toLowerCase().includes(search.toLowerCase()) ||
            t.truck.driver_name.toLowerCase().includes(search.toLowerCase()) ||
            t.start_location_name.toLowerCase().includes(search.toLowerCase()) ||
            t.destination_name.toLowerCase().includes(search.toLowerCase());
        const matchStatus = statusFilter === 'All' || t.status === statusFilter;
        return matchSearch && matchStatus;
    });

    return (
        <div className={styles.page}>
            {/* Header */}
            <motion.div variants={stagger} initial="hidden" animate="show" className={styles.header}>
                <motion.div variants={fadeUp} className={styles.headerLeft}>
                    <div className={styles.breadcrumb}><span>Dashboard</span><ChevronRight size={14} /><span>Fleet</span></div>
                    <h1 className={styles.title}>Fleet Registry</h1>
                    <p className={styles.subtitle}>
                        Showing <strong>{tab === 'trucks' ? filteredTrucks.length : filteredTrips.length}</strong> {tab} from the live database
                        {(trucks.length === 0 && trips.length === 0 && !loading) && (
                            <span className={styles.emptyHint}> — No data yet. Add trucks via Django Admin or the API.</span>
                        )}
                    </p>
                </motion.div>
                <motion.div variants={fadeUp} className={styles.headerRight}>
                    <input
                        className={styles.searchInput}
                        placeholder={`Search ${tab}...`}
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <button className={styles.refreshBtn} onClick={() => fetchAll(true)} disabled={refreshing} title="Refresh data">
                        <RefreshCw size={16} className={refreshing ? styles.spinning : ''} />
                    </button>
                </motion.div>
            </motion.div>

            {/* Tabs */}
            <div className={styles.tabs}>
                {(['trucks', 'trips'] as Tab[]).map(t => (
                    <button
                        key={t}
                        className={`${styles.tab} ${tab === t ? styles.tabActive : ''}`}
                        onClick={() => { setTab(t); setSearch(''); setStatusFilter('All'); }}
                    >
                        {t === 'trucks' ? <Truck size={15} /> : <Activity size={15} />}
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                        <span className={styles.tabCount}>{t === 'trucks' ? trucks.length : trips.length}</span>
                    </button>
                ))}
            </div>

            {loading ? (
                <div className={styles.loader}>
                    <div className={styles.loaderRing} />
                    <span>Loading fleet data from database...</span>
                </div>
            ) : (
                <>
                    {/* ─── TRUCKS TAB ───────────────────────────────────────────────── */}
                    <AnimatePresence mode="wait">
                        {tab === 'trucks' && (
                            <motion.div key="trucks" variants={stagger} initial="hidden" animate="show" exit={{ opacity: 0 }}>
                                {filteredTrucks.length === 0 ? (
                                    <div className={styles.empty}>
                                        <Truck size={48} opacity={0.2} />
                                        <h3>No trucks found</h3>
                                        <p>Add trucks via <a href="http://localhost:8000/admin" target="_blank" rel="noreferrer">Django Admin</a> or the API.</p>
                                    </div>
                                ) : (
                                    <div className={styles.grid}>
                                        {filteredTrucks.map(truck => (
                                            <motion.div key={truck.truck_id} variants={fadeUp} className={styles.card}>
                                                {/* Card header with plate */}
                                                <div className={styles.cardHeader}>
                                                    <div className={styles.plateTag}>
                                                        {truck.license_plate || 'No Plate'}
                                                    </div>
                                                    <span className={`${styles.statusChip} ${truck.active ? styles.chipActive : styles.chipInactive}`}>
                                                        {truck.active ? <><Wifi size={11} /> Active</> : 'Inactive'}
                                                    </span>
                                                </div>

                                                {/* Driver row */}
                                                <div className={styles.cardRow}>
                                                    <User size={14} className={styles.rowIcon} />
                                                    <div>
                                                        <div className={styles.rowLabel}>Driver</div>
                                                        <div className={styles.rowValue}>{truck.driver_name}</div>
                                                    </div>
                                                </div>
                                                {truck.driver_phone && (
                                                    <div className={styles.cardRow}>
                                                        <Shield size={14} className={styles.rowIcon} />
                                                        <div>
                                                            <div className={styles.rowLabel}>Contact</div>
                                                            <div className={styles.rowValue}>{truck.driver_phone}</div>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Cargo */}
                                                <div className={styles.cardRow}>
                                                    <Package size={14} className={styles.rowIcon} />
                                                    <div>
                                                        <div className={styles.rowLabel}>Cargo Type</div>
                                                        <div className={styles.rowValue}>{truck.cargo_type}</div>
                                                    </div>
                                                </div>
                                                <div className={styles.cardRow}>
                                                    <DollarSign size={14} className={styles.rowIcon} />
                                                    <div>
                                                        <div className={styles.rowLabel}>Cargo Value</div>
                                                        <div className={styles.rowValue}>
                                                            ₹{Number(truck.cargo_value).toLocaleString('en-IN')}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Vehicle */}
                                                {truck.vehicle_make_model && (
                                                    <div className={styles.cardRow}>
                                                        <Truck size={14} className={styles.rowIcon} />
                                                        <div>
                                                            <div className={styles.rowLabel}>Vehicle</div>
                                                            <div className={styles.rowValue}>{truck.vehicle_make_model}</div>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Company */}
                                                {truck.company && (
                                                    <div className={styles.cardRow}>
                                                        <MapPin size={14} className={styles.rowIcon} />
                                                        <div>
                                                            <div className={styles.rowLabel}>Company</div>
                                                            <div className={styles.rowValue}>
                                                                {truck.company.name}{truck.company.city ? ` · ${truck.company.city}` : ''}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}

                                                {truck.iot_sensor_id && (
                                                    <div className={styles.sensorId}>
                                                        <Wifi size={11} /> IoT: {truck.iot_sensor_id}
                                                    </div>
                                                )}
                                            </motion.div>
                                        ))}
                                    </div>
                                )}
                            </motion.div>
                        )}

                        {/* ─── TRIPS TAB ── */}
                        {tab === 'trips' && (
                            <motion.div key="trips" variants={stagger} initial="hidden" animate="show" exit={{ opacity: 0 }}>
                                {/* Status filter bar */}
                                <div className={styles.filterBar}>
                                    {tripStatuses.map(s => (
                                        <button
                                            key={s}
                                            className={`${styles.filterChip} ${statusFilter === s ? styles.filterChipActive : ''}`}
                                            onClick={() => setStatusFilter(s)}
                                        >
                                            {s}
                                        </button>
                                    ))}
                                </div>

                                {filteredTrips.length === 0 ? (
                                    <div className={styles.empty}>
                                        <Activity size={48} opacity={0.2} />
                                        <h3>No trips found</h3>
                                        <p>Create trips via <a href="http://localhost:8000/admin" target="_blank" rel="noreferrer">Django Admin</a> or the API.</p>
                                    </div>
                                ) : (
                                    <div className={styles.tripTable}>
                                        <div className={styles.tripTableHeader}>
                                            <span>Truck / Driver</span>
                                            <span>Route</span>
                                            <span>Status</span>
                                            <span>Risk</span>
                                            <span>Departure</span>
                                        </div>
                                        {filteredTrips.map(trip => {
                                            const ss = STATUS_STYLE[trip.status] || STATUS_STYLE.Scheduled;
                                            const rc = RISK_COLOR(trip.current_calculated_risk);
                                            return (
                                                <motion.div key={trip.trip_id} variants={fadeUp} className={styles.tripRow}>
                                                    <div className={styles.tripTruck}>
                                                        <span className={styles.tripPlate}>{trip.truck.license_plate || '—'}</span>
                                                        <span className={styles.tripDriver}>{trip.truck.driver_name}</span>
                                                        <span className={styles.tripCargo}>{trip.truck.cargo_type}</span>
                                                    </div>
                                                    <div className={styles.tripRoute}>
                                                        <span>{trip.start_location_name}</span>
                                                        <ChevronRight size={12} className={styles.routeArrow} />
                                                        <span>{trip.destination_name}</span>
                                                    </div>
                                                    <div>
                                                        <span
                                                            className={styles.statusPill}
                                                            style={{ color: ss.color, background: ss.bg }}
                                                        >
                                                            {ss.label}
                                                        </span>
                                                    </div>
                                                    <div className={styles.riskCell}>
                                                        <div className={styles.riskBar}>
                                                            <div
                                                                className={styles.riskFill}
                                                                style={{ width: `${trip.current_calculated_risk}%`, background: rc }}
                                                            />
                                                        </div>
                                                        <span style={{ color: rc, fontWeight: 700, fontSize: '0.82rem' }}>
                                                            {Math.round(trip.current_calculated_risk)}
                                                        </span>
                                                    </div>
                                                    <div className={styles.tripTime}>
                                                        <Clock size={12} />
                                                        {new Date(trip.start_time).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                                                    </div>
                                                </motion.div>
                                            );
                                        })}
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </>
            )}
        </div>
    );
}
