'use client';

import { useEffect, useState } from 'react';
import styles from './page.module.css';
import { getVisionDetection } from '@/services/apiClient';
import { Camera, AlertCircle, ShieldCheck } from 'lucide-react';

export default function LiveMonitoring() {
    const [detection, setDetection] = useState<{ active: boolean, log: string[] }>({ active: true, log: [] });

    useEffect(() => {
        async function fetchVision() {
            const data = await getVisionDetection();
            setDetection(data);
        }
        fetchVision();
        const interval = setInterval(fetchVision, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1>LIVE MONITORING</h1>
                <p>Real-time Vision AI Analysis</p>
            </div>

            <div className={styles.visionGrid}>
                {/* Camera Feed */}
                <section className={styles.cameraSection}>
                    <div className={styles.panelHeader}>
                        <Camera className={styles.iconAccent} />
                        <h2>Camera Feed: TR102 (Cargo Area)</h2>
                        <div className={styles.statusBadge}>
                            <span className={styles.pulseDot}></span> {detection.active ? 'REC' : 'OFFLINE'}
                        </div>
                    </div>

                    <div className={styles.videoContainer}>
                        {/* Simulated Video Feed with Bounding Boxes */}
                        <div className={styles.videoOverlay}>
                            <div className={styles.boundingBox}>
                                <span className={styles.boxLabel}>Person detected 92%</span>
                            </div>
                        </div>
                        {/* Background pattern simulating video feed */}
                        <div
                            className={styles.videoPlaceholder}
                            style={{
                                backgroundImage: "url('https://images.unsplash.com/photo-1549317661-bd32c8ce0be2?q=80&w=2070&auto=format&fit=crop')",
                                backgroundSize: 'cover',
                                backgroundPosition: 'center',
                                opacity: 0.8
                            }}
                        ></div>
                    </div>
                </section>

                {/* Intelligence Panel */}
                <section className={styles.intelSection}>
                    <div className={styles.logPanel}>
                        <div className={styles.panelHeader}>
                            <AlertCircle className={styles.iconAccent} />
                            <h2>Detection Log</h2>
                        </div>
                        <div className={styles.logList}>
                            {detection.log.map((logItem, i) => (
                                <div key={i} className={styles.logItem}>
                                    <span className={styles.timestamp}>{new Date().toLocaleTimeString()}</span>
                                    <span className={styles.logMessage}>{logItem}</span>
                                </div>
                            ))}
                            <div className={styles.logItem}>
                                <span className={styles.timestamp}>10:45:02 PM</span>
                                <span className={styles.logMessage}>Cargo hatch secured</span>
                            </div>
                            <div className={styles.logItem}>
                                <span className={styles.timestamp}>10:40:15 PM</span>
                                <span className={styles.logMessage}>Vehicle stopped</span>
                            </div>
                        </div>
                    </div>

                    <div className={styles.riskUpdatePanel}>
                        <div className={styles.panelHeader}>
                            <ShieldCheck className={styles.iconAccent} />
                            <h2>Real-time Risk Impact</h2>
                        </div>
                        <div className={styles.impactContent}>
                            <p>Risk Score automatically adjusted based on vision detection.</p>
                            <div className={styles.riskShift}>
                                <span className={styles.oldRisk}>45%</span>
                                <span className={styles.arrow}>→</span>
                                <span className={styles.newRisk}>70%</span>
                            </div>
                            <p className={styles.warningText}>High Risk threshold triggered. Alerts dispatched.</p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
