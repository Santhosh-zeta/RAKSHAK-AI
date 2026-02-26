'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import { getAlerts, EnhancedAlert, SEED_FLEET } from '@/services/apiClient';
import {
    AlertCircle, Filter, CheckCircle2, Search, ChevronDown, ChevronUp,
    MapPin, Navigation, Brain, Clock, ShieldAlert, Bell, Download,
    ArrowUpDown, RotateCcw
} from 'lucide-react';

const AI_EXPLANATIONS: Record<string, string> = {
    Critical: 'Explainability Engine: CRITICAL — Person detected loitering >60s near rear door combined with route deviation. Immediate intervention recommended.',
    High: 'Explainability Engine: Elevated risk — confluence of night transport, high-value cargo, and behavioral anomaly near cargo hatch.',
    Medium: 'Explainability Engine: Moderate risk — stop duration exceeded baseline by 2.3x. No visual confirmation yet. Continue monitoring.',
    Low: 'Explainability Engine: Baseline transit. Journey within normal operating parameters. Routine telemetry only.',
};

const SEVERITY_META: Record<string, { color: string; bg: string; border: string; icon: string }> = {
    Critical: { color: '#dc2626', bg: 'rgba(220,38,38,0.06)', border: '#ef4444', icon: '🔴' },
    High: { color: '#ef4444', bg: 'rgba(239,68,68,0.05)', border: '#f87171', icon: '🟠' },
    Medium: { color: '#d97706', bg: 'rgba(217,119,6,0.05)', border: '#fbbf24', icon: '🟡' },
    Low: { color: '#059669', bg: 'rgba(5,150,105,0.05)', border: '#34d399', icon: '🟢' },
};

const FILTER_ACTIVE_COLORS: Record<string, { bg: string; color: string; border: string }> = {
    All: { bg: '#0284c7', color: 'white', border: '#0284c7' },
    Critical: { bg: '#dc2626', color: 'white', border: '#dc2626' },
    High: { bg: '#ef4444', color: 'white', border: '#ef4444' },
    Medium: { bg: '#f59e0b', color: 'white', border: '#f59e0b' },
    Low: { bg: '#10b981', color: 'white', border: '#10b981' },
};

type SortKey = 'time' | 'severity' | 'truck';
const SEVERITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 };

export default function Alerts() {
    const router = useRouter();
    const [alerts, setAlerts] = useState<EnhancedAlert[]>([]);
    const [filter, setFilter] = useState<'All' | 'Critical' | 'High' | 'Medium' | 'Low'>('All');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);
    const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());
    const [showResolved, setShowResolved] = useState(false); // A4: Resolved tab
    const [sortKey, setSortKey] = useState<SortKey>('severity'); // A6: sort
    const [sortAsc, setSortAsc] = useState(false);
    const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

    // A3: auto-refresh every 30s
    const fetchAlerts = useCallback(async () => {
        const data = await getAlerts();
        const enriched: EnhancedAlert[] = data.map(a => ({
            ...a,
            aiExplanation: a.aiExplanation || AI_EXPLANATIONS[a.level] || AI_EXPLANATIONS['Low'],
            riskScore: a.riskScore ?? (a.level === 'Critical' ? 88 : a.level === 'High' ? 71 : a.level === 'Medium' ? 48 : 15),
            type: a.type || 'System',
        }));
        setAlerts(enriched);
        setLastRefresh(new Date());
    }, []);

    useEffect(() => {
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 30000); // A3
        return () => clearInterval(interval);
    }, [fetchAlerts]);

    // A2: Get real vehicle location from SEED_FLEET matched by truckId
    const getLocation = (truckId?: string) => {
        if (!truckId) return null;
        return SEED_FLEET.find(v => v.info.id === truckId)?.location ?? null;
    };

    // A6: sort handler
    const cycleSort = (key: SortKey) => {
        if (sortKey === key) { setSortAsc(v => !v); } else { setSortKey(key); setSortAsc(false); }
    };

    // A5: CSV Export
    const exportCSV = () => {
        const rows = [
            ['ID', 'Time', 'Truck', 'Level', 'Type', 'Risk Score', 'Message', 'Status'],
            ...alerts.map(a => [
                a.id, a.time, a.truckId ?? '', a.level, a.type ?? '', a.riskScore ?? '', `"${a.message}"`,
                resolvedIds.has(a.id) ? 'Resolved' : 'Active'
            ])
        ];
        const csv = rows.map(r => r.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `rakshak-alerts-${Date.now()}.csv`; a.click();
        URL.revokeObjectURL(url);
    };

    // Toggle expand
    const toggleExpand = (id: string) => setExpandedAlertId(expandedAlertId === id ? null : id);

    // Resolve
    const resolve = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setResolvedIds(prev => new Set([...prev, id]));
        setExpandedAlertId(null);
    };

    // A7: filter counts are based on non-resolved + current search (accurate counts)
    const countForFilter = (f: string) => {
        const base = alerts.filter(a => !resolvedIds.has(a.id));
        const searched = searchQuery
            ? base.filter(a => a.message.toLowerCase().includes(searchQuery.toLowerCase()) || (a.truckId ?? '').toLowerCase().includes(searchQuery.toLowerCase()))
            : base;
        return f === 'All' ? searched.length : searched.filter(a => a.level === f).length;
    };

    // Apply filters + sort
    const filteredAlerts = alerts
        .filter(alert => {
            const isResolved = resolvedIds.has(alert.id);
            if (showResolved) return isResolved;
            if (isResolved) return false;
            const matchFilter = filter === 'All' || alert.level === filter;
            const matchSearch = !searchQuery ||
                alert.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (alert.truckId ?? '').toLowerCase().includes(searchQuery.toLowerCase());
            return matchFilter && matchSearch;
        })
        .sort((a, b) => {
            let diff = 0;
            if (sortKey === 'severity') diff = (SEVERITY_ORDER[a.level] ?? 4) - (SEVERITY_ORDER[b.level] ?? 4);
            else if (sortKey === 'time') diff = a.time > b.time ? -1 : 1;
            else if (sortKey === 'truck') diff = (a.truckId ?? '').localeCompare(b.truckId ?? '');
            return sortAsc ? -diff : diff;
        });

    const criticalCount = alerts.filter(a => a.level === 'Critical' && !resolvedIds.has(a.id)).length;
    const highCount = alerts.filter(a => a.level === 'High' && !resolvedIds.has(a.id)).length;
    const resolvedCount = resolvedIds.size;

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerTop}>
                    <div>
                        <h1 style={{ fontSize: '2rem', fontWeight: 900, color: '#0f172a', marginBottom: 6 }}>
                            Alert Intelligence Center
                        </h1>
                        <p style={{ color: '#64748b', fontSize: '0.9rem', fontWeight: 500 }}>
                            Last refreshed: {lastRefresh.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} · Auto-refreshes every 30s
                        </p> {/* A3 indicator */}
                    </div>
                    <div className={styles.headerStats}>
                        {criticalCount > 0 && (
                            <div className={styles.headerStatBadge} style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)', color: '#dc2626' }}>
                                <AlertCircle size={14} /> {criticalCount} Critical
                            </div>
                        )}
                        {highCount > 0 && (
                            <div className={styles.headerStatBadge} style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}>
                                <ShieldAlert size={14} /> {highCount} High
                            </div>
                        )}
                        <div className={styles.headerStatBadge} style={{ background: 'rgba(2,132,199,0.08)', border: '1px solid rgba(2,132,199,0.2)', color: '#0284c7' }}>
                            <Bell size={14} /> {alerts.filter(a => !resolvedIds.has(a.id)).length} Active
                        </div>
                        {/* A5: Export CSV */}
                        <button
                            onClick={exportCSV}
                            aria-label="Export alerts as CSV"
                            style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '0.5rem 1rem', borderRadius: 999, border: '1px solid #e2e8f0',
                                background: 'white', color: '#475569', fontWeight: 700, fontSize: '0.82rem',
                                cursor: 'pointer', transition: 'all 0.2s'
                            }}
                        >
                            <Download size={14} /> Export CSV
                        </button>
                        {/* Manual refresh button */}
                        <button
                            onClick={fetchAlerts}
                            aria-label="Manually refresh alerts"
                            style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '0.5rem 1rem', borderRadius: 999, border: '1px solid rgba(2,132,199,0.3)',
                                background: 'rgba(2,132,199,0.06)', color: '#0284c7', fontWeight: 700, fontSize: '0.82rem',
                                cursor: 'pointer', transition: 'all 0.2s'
                            }}
                        >
                            <RotateCcw size={13} /> Refresh
                        </button>
                    </div>
                </div>
            </div>

            <div className={styles.alertsLayout}>
                {/* Filter Sidebar */}
                <div className={styles.filterSidebar}>
                    <div className={styles.filterHeader}><Filter size={18} /><h3>Filter Logs</h3></div>

                    {/* A4: Resolved toggle tab */}
                    <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                        <button
                            onClick={() => setShowResolved(false)}
                            aria-label="Show active alerts"
                            style={{
                                flex: 1, padding: '6px 0', borderRadius: 8, border: '1px solid #e2e8f0',
                                background: !showResolved ? '#0284c7' : 'white',
                                color: !showResolved ? 'white' : '#64748b',
                                fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer'
                            }}
                        >Active</button>
                        <button
                            onClick={() => setShowResolved(true)}
                            aria-label="Show resolved alerts"
                            style={{
                                flex: 1, padding: '6px 0', borderRadius: 8, border: '1px solid #e2e8f0',
                                background: showResolved ? '#059669' : 'white',
                                color: showResolved ? 'white' : '#64748b',
                                fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer'
                            }}
                        >
                            Resolved {resolvedCount > 0 && `(${resolvedCount})`}
                        </button>
                    </div>

                    {!showResolved && (
                        <div className={styles.filterGroup}>
                            {(['All', 'Critical', 'High', 'Medium', 'Low'] as const).map(f => {
                                const isActive = filter === f;
                                const activeColors = FILTER_ACTIVE_COLORS[f]; // A8: severity-matched colors
                                return (
                                    <button
                                        key={f}
                                        className={styles.filterBtn}
                                        onClick={() => setFilter(f)}
                                        aria-label={`Filter by ${f}`}
                                        aria-pressed={isActive}
                                        style={isActive ? {
                                            background: activeColors.bg,
                                            color: activeColors.color,
                                            border: `1px solid ${activeColors.border}`
                                        } : undefined}
                                    >
                                        {f !== 'All' && <span>{SEVERITY_META[f]?.icon} </span>}
                                        {f === 'All' ? 'All Alerts' : `${f} Risk`}
                                        {/* A7: counts respect active search */}
                                        <span className={styles.filterCount}>{countForFilter(f)}</span>
                                    </button>
                                );
                            })}
                        </div>
                    )}

                    {/* Alert Source Legend */}
                    <div className={styles.typeLegend}>
                        <div className={styles.typeLegendTitle}>Alert Sources</div>
                        {[
                            { type: 'Vision', color: '#8b5cf6', desc: 'YOLO + DeepSORT' },
                            { type: 'Behavior', color: '#f59e0b', desc: 'IsolationForest' },
                            { type: 'Route', color: '#3b82f6', desc: 'Geofence check' },
                            { type: 'IoT', color: '#10b981', desc: 'Digital Twin' },
                            { type: 'System', color: '#64748b', desc: 'Decision Engine' },
                        ].map(item => (
                            <div key={item.type} className={styles.typeLegendItem}>
                                <div className={styles.typeDot} style={{ background: item.color }} />
                                <span>{item.type}</span>
                                <span className={styles.typeDesc}>{item.desc}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Alerts List */}
                <div className={styles.alertsContent}>
                    <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
                        {/* Search */}
                        <div className={styles.searchContainer} style={{ flex: 1 }}>
                            <Search className={styles.searchIcon} size={18} />
                            <input
                                type="text"
                                className={styles.searchInput}
                                placeholder="Search truck ID, route, alert message..."
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                aria-label="Search alerts"
                            />
                        </div>
                        {/* A6: Sort buttons */}
                        {(['severity', 'time', 'truck'] as SortKey[]).map(key => (
                            <button
                                key={key}
                                onClick={() => cycleSort(key)}
                                aria-label={`Sort by ${key}`}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 4,
                                    padding: '0 12px', borderRadius: 8,
                                    border: `1px solid ${sortKey === key ? '#0284c7' : '#e2e8f0'}`,
                                    background: sortKey === key ? 'rgba(2,132,199,0.08)' : 'white',
                                    color: sortKey === key ? '#0284c7' : '#64748b',
                                    fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
                                    textTransform: 'capitalize'
                                }}
                            >
                                <ArrowUpDown size={12} />
                                {key} {sortKey === key ? (sortAsc ? '↑' : '↓') : ''}
                            </button>
                        ))}
                    </div>

                    {filteredAlerts.length === 0 ? (
                        <div className={styles.emptyState}>
                            <CheckCircle2 size={48} className={styles.successIcon} />
                            <p>{showResolved ? 'No resolved alerts yet.' : 'No active alerts for this filter. System nominal.'}</p>
                        </div>
                    ) : (
                        <div className={styles.alertsList}>
                            {filteredAlerts.map(alert => {
                                const meta = SEVERITY_META[alert.level] || SEVERITY_META['Low'];
                                const isExpanded = expandedAlertId === alert.id;
                                const location = getLocation(alert.truckId); // A2
                                return (
                                    <div
                                        key={alert.id}
                                        className={`${styles.alertCard} ${isExpanded ? styles.expanded : ''}`}
                                        style={{ borderLeftColor: meta.border, background: isExpanded ? meta.bg : undefined }}
                                    >
                                        <div className={styles.alertCardHeader} onClick={() => toggleExpand(alert.id)}>
                                            <div className={styles.alertIcon} style={{ color: meta.color, background: `${meta.color}15` }}>
                                                <AlertCircle size={22} />
                                            </div>
                                            <div className={styles.alertDetails}>
                                                <div className={styles.alertTopRow}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                                                        <span className={styles.alertLevel} style={{ color: meta.color }}>{meta.icon} {alert.level.toUpperCase()}</span>
                                                        <span className={styles.alertTypeBadge} style={{ background: `${meta.color}12`, color: meta.color, border: `1px solid ${meta.color}25` }}>
                                                            {alert.type}
                                                        </span>
                                                        {alert.truckId && <span className={styles.truckBadge}>{alert.truckId}</span>}
                                                    </div>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                        {alert.riskScore !== undefined && (
                                                            <div className={styles.miniRiskBar}>
                                                                <div style={{ width: 50, height: 4, borderRadius: 2, background: '#e2e8f0', overflow: 'hidden' }}>
                                                                    <div style={{ width: `${alert.riskScore}%`, height: '100%', background: meta.color, borderRadius: 2 }} />
                                                                </div>
                                                                <span className={styles.miniRiskScore} style={{ color: meta.color }}>{alert.riskScore}</span>
                                                            </div>
                                                        )}
                                                        <span className={styles.alertTime}><Clock size={12} /> {alert.time}</span>
                                                    </div>
                                                </div>
                                                <p className={styles.alertMessage}>{alert.message}</p>
                                            </div>
                                            <div className={styles.alertActions}>
                                                <button className={styles.expandBtn} aria-label={isExpanded ? 'Collapse alert' : 'Expand alert'}>
                                                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                                </button>
                                            </div>
                                        </div>

                                        {isExpanded && (
                                            <div className={styles.expandedContent}>
                                                {/* AI Explanation */}
                                                <div className={styles.aiExplanationPanel}>
                                                    <div className={styles.aiExplanationHeader}>
                                                        <Brain size={14} style={{ color: '#8b5cf6' }} />
                                                        <span>Explainable AI Analysis</span>
                                                    </div>
                                                    <p className={styles.aiExplanationText}>{alert.aiExplanation}</p>
                                                </div>

                                                <div className={styles.expandedGrid}>
                                                    {/* A2: Real GPS location from SEED_FLEET */}
                                                    <div className={styles.expandedItem}>
                                                        <span className={styles.expandedLabel}><MapPin size={13} /> Location Snapshot</span>
                                                        <span className={styles.expandedValue}>
                                                            {location
                                                                ? `${location.lat.toFixed(4)}°N, ${location.lng.toFixed(4)}°E`
                                                                : 'Location unavailable'}
                                                        </span>
                                                    </div>
                                                    <div className={styles.expandedItem}>
                                                        <span className={styles.expandedLabel}><Navigation size={13} /> Recommended Action</span>
                                                        <span className={styles.expandedValue} style={{ color: meta.color }}>
                                                            {alert.level === 'Critical' ? 'Dispatch rapid response. Lock container. Notify police immediately.' :
                                                                alert.level === 'High' ? 'Alert driver and control room. Request visual confirmation.' :
                                                                    'Monitor live feeds. Notify convoy leader of potential risk.'}
                                                        </span>
                                                    </div>
                                                </div>

                                                <div className={styles.expandedActions}>
                                                    {/* A1: "View on Map" now navigates to dashboard */}
                                                    <button
                                                        className={styles.actionBtnSecondary}
                                                        onClick={(e) => { e.stopPropagation(); router.push('/dashboard'); }}
                                                        aria-label="View vehicle on map"
                                                    >
                                                        View on Map
                                                    </button>
                                                    {!resolvedIds.has(alert.id) && (
                                                        <button
                                                            className={styles.actionBtnPrimary}
                                                            style={{ background: meta.color }}
                                                            onClick={(e) => resolve(alert.id, e)}
                                                            aria-label="Acknowledge and resolve this alert"
                                                        >
                                                            <CheckCircle2 size={14} /> Acknowledge &amp; Resolve
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
