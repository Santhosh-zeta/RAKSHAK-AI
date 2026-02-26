'use client';

import { useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import styles from './page.module.css';
import { getFleetData, getAlerts, triggerSimulation, FleetVehicle, Alert } from '@/services/apiClient';
import { useToast } from '@/components/Toast';
import {
    MapPin, Activity, Truck, Banknote, ShieldAlert, BarChart3,
    Crosshair, Terminal, ArrowUpRight, Signal, Zap, CheckCircle2, ExternalLink
} from 'lucide-react';

// Dynamically import MapView (SVG-based — no external dep)
const MapView = dynamic(() => import('@/components/MapView'), {
    ssr: false,
    loading: () => (
        <div className={styles.mapLoading}>
            <div className={styles.radarLoader}></div>
            <p>Initializing Map Engine...</p>
        </div>
    )
});

// Error Boundary (G5)
import { Component, ReactNode } from 'react';
class ErrorBoundary extends Component<{ children: ReactNode; fallback?: ReactNode }, { hasError: boolean }> {
    constructor(props: any) { super(props); this.state = { hasError: false }; }
    static getDerivedStateFromError() { return { hasError: true }; }
    render() {
        if (this.state.hasError) return this.props.fallback || <div className={styles.errorFallback}>Component failed to load.</div>;
        return this.props.children;
    }
}

const SEVERITY_BORDER: Record<string, string> = {
    Critical: '#dc2626', High: '#ef4444', Medium: '#f59e0b', Low: '#10b981'
};

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
    Alert: { color: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
    'In Transit': { color: '#0284c7', bg: 'rgba(2,132,199,0.08)' },
    Scheduled: { color: '#9333ea', bg: 'rgba(147,51,234,0.08)' },
};

export default function Dashboard() {
    const [fleet, setFleet] = useState<FleetVehicle[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState<'All' | 'High Risk' | 'In Transit'>('All');
    const [demoStatus, setDemoStatus] = useState<'idle' | 'running' | 'done'>('idle');
    const [terminalTick, setTerminalTick] = useState(0);
    const { showToast, ToastElement } = useToast();

    const fetchData = useCallback(async () => {
        try {
            const [fleetData, alertsData] = await Promise.all([getFleetData(), getAlerts()]);
            setFleet(fleetData);
            setAlerts(alertsData);
        } catch (error) {
            console.error('Error fetching data', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Poll with visibility API (D11, G6) — pause polling when tab is hidden
    useEffect(() => {
        fetchData();
        let interval: ReturnType<typeof setInterval>;

        const startPolling = () => {
            interval = setInterval(() => {
                if (!document.hidden) fetchData();
            }, 30000); // D11: increased to 30s
        };

        const handleVisibilityChange = () => {
            if (!document.hidden) fetchData(); // refresh on tab focus
        };

        startPolling();
        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => {
            clearInterval(interval);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [fetchData]);

    // Terminal ticker (D10)
    useEffect(() => {
        const t = setInterval(() => setTerminalTick(v => v + 1), 3000);
        return () => clearInterval(t);
    }, []);

    const handleDemo = async () => {
        const targetTrip = fleet.find(v => v.risk.level === 'High' || v.risk.level === 'Critical');
        if (!targetTrip) return;
        setDemoStatus('running');
        const ok = await triggerSimulation(targetTrip.trip_id);
        if (ok) {
            setDemoStatus('done');
            showToast('🚨 Demo scenario triggered! New alerts are active.', 'warning'); // G2
            setTimeout(() => setDemoStatus('idle'), 3000);
            setTimeout(() => fetchData(), 1000);
        } else {
            setDemoStatus('idle');
            showToast('Failed to trigger scenario — check backend connection.', 'error');
        }
    };

    if (isLoading) {
        return (
            <div className={styles.loadingContainer}>
                <div className={styles.loaderCore}>
                    <div className={styles.loaderRing}></div>
                    <div className={styles.loaderRing2}></div>
                    <ShieldAlert size={32} className={styles.loaderIcon} />
                </div>
                <h2>Rakshak Command Center Starting...</h2>
                <div className={styles.loadingBar}><div className={styles.loadingFill}></div></div>
            </div>
        );
    }

    const highRiskCount = fleet.filter(v => v.risk.level === 'High' || v.risk.level === 'Critical').length;
    const totalValue = fleet.reduce((acc, v) => acc + v.info.value, 0);
    // D8: Compute operational efficiency from low-risk fraction
    const operationalPct = fleet.length > 0
        ? Math.round((fleet.filter(v => v.risk.level === 'Low' || v.risk.level === 'Medium').length / fleet.length) * 100)
        : 92;
    const avgRisk = fleet.length > 0
        ? Math.round(fleet.reduce((acc, v) => acc + v.risk.score, 0) / fleet.length) : 0;
    const avgRiskColor = avgRisk >= 70 ? '#ef4444' : avgRisk >= 45 ? '#f59e0b' : '#10b981';

    const filteredFleet = fleet.filter(v => {
        if (activeFilter === 'High Risk') return v.risk.level === 'High' || v.risk.level === 'Critical';
        if (activeFilter === 'In Transit') return v.status === 'In Transit';
        return true;
    });

    // D10: Cycle through all fleet in terminal log
    const terminalVehicles = fleet.length > 0
        ? [fleet[terminalTick % fleet.length], fleet[(terminalTick + 1) % fleet.length], fleet[(terminalTick + 2) % fleet.length]]
        : [];

    return (
        <div className={styles.dashboardContainer}>
            {ToastElement /* G2 */}

            <div className={styles.topControls}>
                <h1 className={styles.pageTitle}>Fleet Command <span>/ Live Intel</span></h1>
                <div className={styles.filterGroup}>
                    {(['All', 'In Transit', 'High Risk'] as const).map(filter => (
                        <button
                            key={filter}
                            onClick={() => setActiveFilter(filter)}
                            className={`${styles.filterBtn} ${activeFilter === filter ? styles.activeFilter : ''}`}
                            aria-label={`Filter: ${filter}`} // G10
                        >
                            {filter} {filter === 'High Risk' && highRiskCount > 0 && <span className={styles.filterBadge}>{highRiskCount}</span>}
                        </button>
                    ))}
                </div>
                <button
                    onClick={handleDemo}
                    disabled={demoStatus === 'running'}
                    className={styles.demoBtn} // D2: moved to CSS class
                    aria-label="Trigger demo theft scenario"  // G10
                    data-status={demoStatus}
                >
                    {demoStatus === 'running' ? <Activity size={16} className={styles.spinIcon} /> : demoStatus === 'done' ? <CheckCircle2 size={16} /> : <Zap size={16} />}
                    {demoStatus === 'running' ? 'Triggering...' : demoStatus === 'done' ? 'Scenario Active!' : '🚨 Trigger Demo'}
                </button>
            </div>

            {/* Stats Grid */}
            <section className={styles.statsGrid}>
                {/* Active Fleet */}
                <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Truck size={20} className={styles.iconAccent} /></div>
                        <span className={styles.statLabel}>Active Consignments</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={styles.statValue}>{fleet.length}</h2>
                        <div className={styles.statSparkline}><Activity size={32} className={styles.sparklineGood} /></div>
                    </div>
                    <div className={styles.statFooter}>
                        <ArrowUpRight size={14} className={styles.iconGood} />
                        <span>{fleet.filter(v => v.status === 'Alert').length} on alert, {fleet.filter(v => v.status === 'In Transit').length} in transit</span>
                    </div>
                </div>

                {/* Critical Threats */}
                <div className={`${styles.statCard} ${highRiskCount > 0 ? styles.statCardWarning : ''}`}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapperWarning}>
                            <ShieldAlert size={20} className={highRiskCount > 0 ? styles.iconHigh : styles.iconSafe} />
                        </div>
                        <span className={styles.statLabel}>Critical Threats</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={`${styles.statValue} ${highRiskCount > 0 ? styles.textHigh : styles.textSafe}`}>{highRiskCount}</h2>
                        <div className={styles.flexStack}>
                            {highRiskCount > 0 && <span className={styles.pulseTag}>ACTION REQUIRED</span>}
                        </div>
                    </div>
                    <div className={styles.statFooter}><span>Real-time AI behavioral analysis active</span></div>
                </div>

                {/* Assets Monitored — D8: computed from real data */}
                <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Banknote size={20} className={styles.iconAccent} /></div>
                        <span className={styles.statLabel}>Assets Monitored</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={styles.statValue}>₹{(totalValue / 10000000).toFixed(2)}Cr</h2>
                        <div className={styles.circularProgress}>
                            <svg viewBox="0 0 36 36" className={styles.circularSvg}>
                                <path className={styles.circleBg} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path className={styles.circleFill} strokeDasharray={`${operationalPct}, 100`}
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                            </svg>
                            <span className={styles.circleText}>{operationalPct}%</span>
                        </div>
                    </div>
                    <div className={styles.statFooter}><span>{operationalPct}% fleet operational efficiency</span></div>
                </div>

                {/* Fleet Avg Risk Gauge */}
                <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><BarChart3 size={20} className={styles.iconAccent} /></div>
                        <span className={styles.statLabel}>Fleet Avg Risk</span>
                    </div>
                    <div className={styles.statBody} style={{ justifyContent: 'center' }}>
                        <div className={styles.riskGaugeWrap}>
                            <svg viewBox="0 0 36 20" className={styles.riskGaugeSvg}>
                                <path d="M3 18 A 15 15 0 0 1 33 18" fill="none" stroke="#e2e8f0" strokeWidth="3.5" strokeLinecap="round" />
                                <path d="M3 18 A 15 15 0 0 1 33 18" fill="none" stroke={avgRiskColor} strokeWidth="3.5" strokeLinecap="round"
                                    strokeDasharray={`${(avgRisk / 100) * 47.12} 47.12`} // R4: correct arc circumference
                                    style={{ transition: 'stroke-dasharray 1.2s ease' }}
                                />
                            </svg>
                            <div className={styles.riskGaugeLabel}>
                                <span className={styles.riskGaugeValue} style={{ color: avgRiskColor }}>{avgRisk}</span>
                                <span className={styles.riskGaugeSub}>/ 100</span>
                            </div>
                        </div>
                    </div>
                    <div className={styles.statFooter}>
                        <span style={{ color: avgRiskColor, fontWeight: 700 }}>
                            {avgRisk >= 70 ? '🔴 HIGH THREAT' : avgRisk >= 45 ? '🟡 MODERATE RISK' : '🟢 LOW RISK'}
                        </span>
                    </div>
                </div>
            </section>

            <div className={styles.mainGrid}>
                {/* Map — D12: taller via CSS */}
                <section className={styles.mapSection}>
                    <div className={styles.panelHeader}>
                        <div className={styles.headerLeft}>
                            <MapPin className={styles.iconAccent} />
                            <h2>Global Tracking Matrix</h2>
                        </div>
                        <div className={styles.statusBadge}>
                            <Signal size={12} className={styles.iconBlink} /> Live Uplink
                        </div>
                    </div>
                    <div className={styles.mapContainer}>
                        <div className={styles.mapGlow}></div>
                        <div className={styles.mapPlaceholder}>
                            <ErrorBoundary fallback={<div className={styles.errorFallback}>Map failed to load.</div>}>
                                <MapView fleet={fleet} />
                            </ErrorBoundary>
                        </div>
                        {/* Terminal Overlay — D10: cycles through all fleet, shows GPS coords */}
                        <div className={styles.mapOverlayTerminal}>
                            <div className={styles.terminalHeader}>SYSTEM LOG</div>
                            <div className={styles.terminalBody}>
                                {terminalVehicles.map((f, i) => (
                                    <div key={`${f.info.id}-${terminalTick}-${i}`} className={styles.terminalLine}>
                                        <span className={styles.tTime}>{new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                                        <span className={styles.tSys}>[GPS]</span>
                                        <span className={styles.tMsg}>{f.info.id} @ [{f.location.lat.toFixed(4)}°N, {f.location.lng.toFixed(4)}°E] — Risk: {f.risk.score}</span>
                                    </div>
                                ))}
                                <div className={styles.terminalLine}><span className={styles.tBlink}>_</span></div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Alerts Feed — D3, D4, D5: clickable, color-coded, type badge */}
                <section className={styles.alertsPanel}>
                    <div className={styles.panelHeader}>
                        <div className={styles.headerLeft}>
                            <Terminal className={styles.iconHigh} />
                            <h2>Threat Feed</h2>
                        </div>
                        <Link href="/alerts" className={styles.viewAllLink} aria-label="View all alerts">
                            View All <ExternalLink size={12} />
                        </Link>
                    </div>
                    <div className={styles.alertsList}>
                        {alerts.length === 0 ? (
                            <div className={styles.emptyAlerts}>No active threats.</div>
                        ) : (
                            alerts.slice(0, 8).map(alert => (
                                <Link key={alert.id} href="/alerts" className={styles.alertCard} // D3: clickable
                                    style={{ borderLeft: `3px solid ${SEVERITY_BORDER[alert.level] || '#94a3b8'}` }} // D4
                                >
                                    <div className={styles.alertContent}>
                                        <div className={styles.alertHeaderRow}>
                                            <span className={styles.alertTarget}>{alert.truckId}</span>
                                            {/* D5: type badge */}
                                            {alert.type && (
                                                <span className={styles.alertTypePill} data-type={alert.type}>{alert.type}</span>
                                            )}
                                            <span className={styles.alertTimeLabel}>{alert.time}</span>
                                        </div>
                                        <p className={styles.alertMessageText}>{alert.message}</p>
                                    </div>
                                </Link>
                            ))
                        )}
                    </div>
                </section>
            </div>

            {/* Fleet Telemetry Table — D1, D6, D7 */}
            <section className={styles.dataGridSection}>
                <div className={styles.panelHeader}>
                    <div className={styles.headerLeft}>
                        <BarChart3 className={styles.iconAccent} />
                        <h2>Deep Fleet Telemetry</h2>
                    </div>
                    <span className={styles.tableSubline}>{filteredFleet.length} consignments shown</span>
                </div>
                <div className={styles.tableContainer}>
                    <table className={styles.dataTable}>
                        <thead>
                            <tr>
                                <th>UNIT ID</th>
                                <th>STATUS</th>
                                <th>ROUTE VECTOR</th>
                                <th>CARGO YIELD</th>
                                <th>AI RISK SCORE</th>
                                <th>LAST PING</th> {/* D1 */}
                                <th>ACTION</th> {/* D6 */}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredFleet.map((vehicle, i) => {
                                // D1: Real-ish timestamps based on index offset
                                const pingTime = new Date(Date.now() - i * 47000);
                                const pingLabel = i === 0 ? 'Just now' : `${Math.round(i * 47 / 60)}m ago`;
                                const statusStyle = STATUS_STYLE[vehicle.status] || { color: '#475569', bg: 'rgba(71,85,105,0.08)' };
                                return (
                                    <tr key={vehicle.info.id} className={styles.dataRow}>
                                        <td className={styles.colId}>
                                            <Crosshair size={14} className={styles.iconMuted} />
                                            {vehicle.info.id}
                                        </td>
                                        <td>
                                            {/* D7: color-coded status badge */}
                                            <span className={styles.gridStatus} style={{ color: statusStyle.color, background: statusStyle.bg, border: `1px solid ${statusStyle.color}30` }}>
                                                {vehicle.status === 'Alert' && '⚠ '}{vehicle.status}
                                            </span>
                                        </td>
                                        <td className={styles.colRoute}>{vehicle.info.route}</td>
                                        <td className={styles.colValue}>₹{(vehicle.info.value / 100000).toFixed(1)}L</td>
                                        <td>
                                            <div className={styles.riskBarContainer}>
                                                <div className={`${styles.riskBarFill} ${styles[`riskBg${vehicle.risk.level}`]}`}
                                                    style={{ width: `${vehicle.risk.score}%` }} />
                                                <span className={styles.riskBarText}>{vehicle.risk.score}/100</span>
                                            </div>
                                        </td>
                                        <td className={styles.colPing}>{pingLabel}</td> {/* D1 */}
                                        {/* D6: View Details */}
                                        <td>
                                            <Link href="/alerts" className={styles.viewDetailsBtn} aria-label={`View details for ${vehicle.info.id}`}>
                                                Details →
                                            </Link>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}
