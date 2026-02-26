'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import styles from './page.module.css';
import { getFleetData, getAlerts, FleetVehicle, Alert } from '@/services/apiClient';
import { Camera, MapPin, Activity, AlertTriangle, Truck, Package, Banknote, Navigation, ShieldAlert, BarChart3, Crosshair, Terminal, ArrowUpRight, Signal } from 'lucide-react';

// Dynamically import MapView to disable Server-Side Rendering (Leaflet relies on window)
const MapView = dynamic(() => import('@/components/MapView'), {
    ssr: false,
    loading: () => (
        <div className={styles.mapLoading}>
            <div className={styles.radarLoader}></div>
            <p>Initializing Sat-Link...</p>
        </div>
    )
});

export default function Dashboard() {
    const [fleet, setFleet] = useState<FleetVehicle[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState<'All' | 'High Risk' | 'In Transit'>('All');

    // Poll for live data
    useEffect(() => {
        async function fetchData() {
            try {
                const [fleetData, alertsData] = await Promise.all([
                    getFleetData(),
                    getAlerts()
                ]);
                setFleet(fleetData);
                setAlerts(alertsData);
            } catch (error) {
                console.error("Error fetching live data", error);
            } finally {
                setIsLoading(false);
            }
        }

        fetchData();
        const interval = setInterval(fetchData, 4000); // refresh every 4s for demo speed
        return () => clearInterval(interval);
    }, []);

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

    const filteredFleet = fleet.filter(v => {
        if (activeFilter === 'High Risk') return v.risk.level === 'High' || v.risk.level === 'Critical';
        if (activeFilter === 'In Transit') return v.status === 'In Transit';
        return true;
    });

    return (
        <div className={styles.dashboardContainer}>
            <div className={styles.topControls}>
                <h1 className={styles.pageTitle}>Fleet Command <span>/ Live Intel</span></h1>
                <div className={styles.filterGroup}>
                    {['All', 'In Transit', 'High Risk'].map(filter => (
                        <button
                            key={filter}
                            onClick={() => setActiveFilter(filter as any)}
                            className={`${styles.filterBtn} ${activeFilter === filter ? styles.activeFilter : ''}`}
                        >
                            {filter} {filter === 'High Risk' && highRiskCount > 0 && <span className={styles.filterBadge}>{highRiskCount}</span>}
                        </button>
                    ))}
                </div>
            </div>

            {/* Top Banner: Advanced Metrics */}
            <section className={styles.statsGrid}>
                {/* Active Fleet Card */}
                <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Truck size={20} className={styles.iconAccent} /></div>
                        <span className={styles.statLabel}>Active Consignments</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={styles.statValue}>{fleet.length}</h2>
                        <div className={styles.statSparkline}>
                            <Activity size={32} className={styles.sparklineGood} />
                        </div>
                    </div>
                    <div className={styles.statFooter}>
                        <ArrowUpRight size={14} className={styles.iconGood} />
                        <span>12% above daily average</span>
                    </div>
                </div>

                {/* Risk Card */}
                <div className={`${styles.statCard} ${highRiskCount > 0 ? styles.statCardWarning : ''}`}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapperWarning}>
                            <ShieldAlert size={20} className={highRiskCount > 0 ? styles.iconHigh : styles.iconSafe} />
                        </div>
                        <span className={styles.statLabel}>Critical Threats</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={`${styles.statValue} ${highRiskCount > 0 ? styles.textHigh : styles.textSafe}`}>
                            {highRiskCount}
                        </h2>
                        <div className={styles.flexStack}>
                            {highRiskCount > 0 && <span className={styles.pulseTag}>ACTION REQUIRED</span>}
                        </div>
                    </div>
                    <div className={styles.statFooter}>
                        <span>Real-time AI behavioral analysis active</span>
                    </div>
                </div>

                {/* Capital Card */}
                <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                        <div className={styles.statIconWrapper}><Banknote size={20} className={styles.iconAccent} /></div>
                        <span className={styles.statLabel}>Assets Monitored</span>
                    </div>
                    <div className={styles.statBody}>
                        <h2 className={styles.statValue}>₹{(totalValue / 10000000).toFixed(2)}Cr</h2>
                        <div className={styles.circularProgress}>
                            <svg viewBox="0 0 36 36" className={styles.circularSvg}>
                                <path className={styles.circleBg}
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path className={styles.circleFill}
                                    strokeDasharray="92, 100"
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                            </svg>
                            <span className={styles.circleText}>92%</span>
                        </div>
                    </div>
                    <div className={styles.statFooter}>
                        <span>Fleet operational efficiency</span>
                    </div>
                </div>
            </section>

            <div className={styles.mainGrid}>
                {/* Center Column: Immersive Map */}
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
                            <MapView fleet={fleet} />
                        </div>
                        {/* Terminal Overlay on Map */}
                        <div className={styles.mapOverlayTerminal}>
                            <div className={styles.terminalHeader}>SYSTEM LOG</div>
                            <div className={styles.terminalBody}>
                                {fleet.slice(0, 3).map(f => (
                                    <div key={f.info.id} className={styles.terminalLine}>
                                        <span className={styles.tTime}>{new Date().toLocaleTimeString()}</span>
                                        <span className={styles.tSys}>[SAT]</span>
                                        <span className={styles.tMsg}>Tracked {f.info.id} at [{f.location.lat.toFixed(4)}, {f.location.lng.toFixed(4)}] Risk: {f.risk.score}</span>
                                    </div>
                                ))}
                                <div className={styles.terminalLine}>
                                    <span className={styles.tBlink}>_</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Right Column: Alerts Feed */}
                <section className={styles.alertsPanel}>
                    <div className={styles.panelHeader}>
                        <div className={styles.headerLeft}>
                            <Terminal className={styles.iconHigh} />
                            <h2>Threat Feed</h2>
                        </div>
                    </div>
                    <div className={styles.alertsList}>
                        {alerts.length === 0 ? (
                            <div className={styles.emptyAlerts}>No active threats.</div>
                        ) : (
                            alerts.map(alert => (
                                <div key={alert.id} className={styles.alertCard}>
                                    <div className={`${styles.alertIndicator} ${styles[`indicator${alert.level}`]}`}></div>
                                    <div className={styles.alertContent}>
                                        <div className={styles.alertHeaderRow}>
                                            <span className={styles.alertTarget}>{alert.truckId}</span>
                                            <span className={styles.alertTimeLabel}>{alert.time}</span>
                                        </div>
                                        <p className={styles.alertMessageText}>{alert.message}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </section>
            </div>

            {/* Bottom Row: Dense Data Grid */}
            <section className={styles.dataGridSection}>
                <div className={styles.panelHeader}>
                    <div className={styles.headerLeft}>
                        <BarChart3 className={styles.iconAccent} />
                        <h2>Deep Fleet Telemetry</h2>
                    </div>
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
                                <th>LAST PING</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredFleet.map(vehicle => (
                                <tr key={vehicle.info.id} className={styles.dataRow}>
                                    <td className={styles.colId}>
                                        <Crosshair size={14} className={styles.iconMuted} />
                                        {vehicle.info.id}
                                    </td>
                                    <td>
                                        <span className={styles.gridStatus}>{vehicle.status}</span>
                                    </td>
                                    <td className={styles.colRoute}>{vehicle.info.route}</td>
                                    <td className={styles.colValue}>₹{(vehicle.info.value / 100000).toFixed(1)}L</td>
                                    <td>
                                        <div className={styles.riskBarContainer}>
                                            <div
                                                className={`${styles.riskBarFill} ${styles[`riskBg${vehicle.risk.level}`]}`}
                                                style={{ width: `${vehicle.risk.score}%` }}
                                            ></div>
                                            <span className={styles.riskBarText}>{vehicle.risk.score}/100</span>
                                        </div>
                                    </td>
                                    <td className={styles.colPing}>Just now</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}
