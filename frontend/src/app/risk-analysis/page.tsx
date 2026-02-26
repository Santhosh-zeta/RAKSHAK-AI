'use client';

import { useState } from 'react';
import styles from './page.module.css';
import { Shield, BrainCircuit, Box, Monitor, HardHat, Shirt } from 'lucide-react';

const cargoOptions = [
    { id: 'Steel', icon: HardHat, label: 'Steel' },
    { id: 'Electronics', icon: Monitor, label: 'Electronics' },
    { id: 'Cement', icon: Box, label: 'Cement' },
    { id: 'Textiles', icon: Shirt, label: 'Textiles' }
];

export default function RiskAnalysis() {
    const [cargoType, setCargoType] = useState('Electronics');
    const [route, setRoute] = useState('Chennai → Mumbai');
    const [time, setTime] = useState('Night');
    const [value, setValue] = useState('1500000');

    const [isPredicting, setIsPredicting] = useState(false);
    const [result, setResult] = useState<{ score: number, reasons: string[] } | null>(null);

    const handlePredict = (e: React.FormEvent) => {
        e.preventDefault();
        setIsPredicting(true);

        // Simulate API delay
        setTimeout(() => {
            // Dummy logic to generate risk score based on inputs
            let score = 40;
            let reasons = [];

            if (time === 'Night') { score += 25; reasons.push('Night Travel Increases Risk'); }
            if (cargoType === 'Electronics') { score += 15; reasons.push('High value, easily fenceable cargo'); }
            if (route.includes('Mumbai')) { score += 10; reasons.push('Route passes through known risk zones'); }

            setResult({ score, reasons });
            setIsPredicting(false);
        }, 1500);
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1>RISK ANALYSIS</h1>
                <p>Predictive Engine Simulation</p>
            </div>

            <div className={styles.analysisGrid}>
                {/* Input Form */}
                <section className={styles.formSection}>
                    <form className={styles.predictionForm} onSubmit={handlePredict}>
                        <div className={styles.formGroup}>
                            <label>Cargo Type</label>
                            <div className={styles.cargoGrid}>
                                {cargoOptions.map(option => (
                                    <div
                                        key={option.id}
                                        className={`${styles.cargoCard} ${cargoType === option.id ? styles.selected : ''}`}
                                        onClick={() => setCargoType(option.id)}
                                    >
                                        <option.icon size={24} className={styles.cargoIcon} />
                                        <span>{option.label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className={styles.formGroup}>
                            <label>Route</label>
                            <input
                                type="text"
                                value={route}
                                onChange={(e) => setRoute(e.target.value)}
                                placeholder="e.g., Chennai → Mumbai"
                            />
                        </div>

                        <div className={styles.formGroup}>
                            <label>Travel Time</label>
                            <select value={time} onChange={(e) => setTime(e.target.value)}>
                                <option value="Day">Day Travel</option>
                                <option value="Night">Night Travel</option>
                            </select>
                        </div>

                        <div className={styles.formGroup}>
                            <label>Cargo Value (₹)</label>
                            <input
                                type="number"
                                value={value}
                                onChange={(e) => setValue(e.target.value)}
                            />
                        </div>

                        <button
                            type="submit"
                            className={styles.predictBtn}
                            disabled={isPredicting}
                        >
                            {isPredicting ? 'Analyzing Risk Profile...' : 'Predict Risk'}
                            <BrainCircuit size={20} />
                        </button>
                    </form>
                </section>

                {/* Prediction Results */}
                <section className={styles.resultSection}>
                    {isPredicting ? (
                        <div className={styles.loadingState}>
                            <BrainCircuit size={48} className={styles.spinnerIcon} />
                            <h3>Running AI Intel Matrix...</h3>
                            <div className={styles.progressBar}>
                                <div className={styles.progressFill}></div>
                            </div>
                            <p className={styles.loadingText}>Scanning route vectors across thousands of historic incidents.</p>
                        </div>
                    ) : result ? (
                        <div className={styles.resultCard}>
                            <div className={styles.resultHeader}>
                                <Shield className={styles.iconAccent} size={32} />
                                <h2>AI Prediction Complete</h2>
                            </div>

                            <div className={styles.scoreDisplay}>
                                <span className={styles.scoreLabel}>THEFT RISK</span>
                                <span className={`${styles.scoreValue} ${result.score > 70 ? styles.highScore : styles.medScore}`}>
                                    {result.score}%
                                </span>
                            </div>

                            <div className={styles.reasonList}>
                                <h3>Primary Risk Factors:</h3>
                                <ul>
                                    {result.reasons.map((r, i) => (
                                        <li key={i}>{r}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    ) : (
                        <div className={styles.emptyState}>
                            <BrainCircuit size={48} className={styles.emptyIcon} />
                            <p>Enter trip details and click Predict to activate the AI analysis engine.</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
