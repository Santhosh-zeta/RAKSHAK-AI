'use client';

import { useEffect, useState } from 'react';
import styles from './page.module.css';
import { getAlerts, Alert } from '@/services/apiClient';
import { AlertCircle, Filter, CheckCircle2, Search, ChevronDown, ChevronUp, MapPin, Navigation } from 'lucide-react';

export default function Alerts() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [filter, setFilter] = useState<'All' | 'High' | 'Medium' | 'Low'>('All');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);

    useEffect(() => {
        async function fetchAlerts() {
            // Fetch alerts from the backend
            const data = await getAlerts();

            // For demo purposes, let's artificially expand the list if it's too short
            const expandedData = [...data];
            if (expandedData.length < 5) {
                expandedData.push({ id: '4', time: '09:15 PM', message: 'Route deviation detected', level: 'Medium' });
                expandedData.push({ id: '5', time: '08:00 PM', message: 'Journey started from origin', level: 'Low' });
                expandedData.push({ id: '6', time: '07:30 PM', message: 'Pre-trip scan completed', level: 'Low' });
            }

            setAlerts(expandedData);
        }
        fetchAlerts();
    }, []);

    const filteredAlerts = alerts.filter(alert => {
        const matchesFilter = filter === 'All' || alert.level === filter;
        const matchesSearch = alert.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
            alert.id.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFilter && matchesSearch;
    });

    const toggleExpand = (id: string) => {
        if (expandedAlertId === id) setExpandedAlertId(null);
        else setExpandedAlertId(id);
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1>SYSTEM ALERTS</h1>
                <p>Complete Threat Intelligence Log</p>
            </div>

            <div className={styles.alertsLayout}>
                {/* Filters Sidebar */}
                <div className={styles.filterSidebar}>
                    <div className={styles.filterHeader}>
                        <Filter size={18} />
                        <h3>Filter Logs</h3>
                    </div>

                    <div className={styles.filterGroup}>
                        <button
                            className={`${styles.filterBtn} ${filter === 'All' ? styles.active : ''}`}
                            onClick={() => setFilter('All')}
                        >
                            All Alerts
                        </button>
                        <button
                            className={`${styles.filterBtn} ${styles.highFilter} ${filter === 'High' ? styles.active : ''}`}
                            onClick={() => setFilter('High')}
                        >
                            High Risk
                        </button>
                        <button
                            className={`${styles.filterBtn} ${styles.mediumFilter} ${filter === 'Medium' ? styles.active : ''}`}
                            onClick={() => setFilter('Medium')}
                        >
                            Medium Risk
                        </button>
                        <button
                            className={`${styles.filterBtn} ${styles.lowFilter} ${filter === 'Low' ? styles.active : ''}`}
                            onClick={() => setFilter('Low')}
                        >
                            Informational
                        </button>
                    </div>
                </div>

                {/* Alerts List */}
                <div className={styles.alertsContent}>
                    {/* Search Bar */}
                    <div className={styles.searchContainer}>
                        <Search className={styles.searchIcon} size={20} />
                        <input
                            type="text"
                            className={styles.searchInput}
                            placeholder="Search by Truck ID, route, or alert message..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    {filteredAlerts.length === 0 ? (
                        <div className={styles.emptyState}>
                            <CheckCircle2 size={48} className={styles.successIcon} />
                            <p>No alerts found for this filter criteria.</p>
                        </div>
                    ) : (
                        <div className={styles.alertsList}>
                            {filteredAlerts.map(alert => (
                                <div key={alert.id} className={`${styles.alertCard} ${styles[`level${alert.level}`]} ${expandedAlertId === alert.id ? styles.expanded : ''}`}>
                                    <div className={styles.alertCardHeader} onClick={() => toggleExpand(alert.id)}>
                                        <div className={styles.alertIcon}>
                                            <AlertCircle size={24} />
                                        </div>
                                        <div className={styles.alertDetails}>
                                            <div className={styles.alertTopRow}>
                                                <span className={styles.alertLevel}>{alert.level.toUpperCase()} PRIORITY • TR10{alert.id}</span>
                                                <span className={styles.alertTime}>{alert.time}</span>
                                            </div>
                                            <p className={styles.alertMessage}>{alert.message}</p>
                                        </div>
                                        <div className={styles.alertActions}>
                                            <button className={styles.expandBtn}>
                                                {expandedAlertId === alert.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Expandable Content Area */}
                                    {expandedAlertId === alert.id && (
                                        <div className={styles.expandedContent}>
                                            <div className={styles.expandedGrid}>
                                                <div className={styles.expandedItem}>
                                                    <span className={styles.expandedLabel}><MapPin size={14} /> Location Snapshot</span>
                                                    <span className={styles.expandedValue}>Lat: {(18.5204 + parseFloat(alert.id) * 0.01).toFixed(4)}, Lng: {(73.8567 + parseFloat(alert.id) * 0.01).toFixed(4)}</span>
                                                </div>
                                                <div className={styles.expandedItem}>
                                                    <span className={styles.expandedLabel}><Navigation size={14} /> Recommended Action</span>
                                                    <span className={styles.expandedValue}>{alert.level === 'High' ? 'Dispatch rapid response team and halt vehicle immediately.' : 'Monitor live feeds and notify convoy leader of potential risk.'}</span>
                                                </div>
                                            </div>
                                            <div className={styles.expandedActions}>
                                                <button className={styles.actionBtnSecondary}>View Tracking Map</button>
                                                <button className={styles.actionBtnPrimary}>Acknowledge Threat</button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
