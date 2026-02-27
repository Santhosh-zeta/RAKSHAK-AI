'use client';

import { useEffect, useState, useRef } from 'react';
import { FleetVehicle } from '@/services/apiClient';

interface MapViewProps {
    fleet: FleetVehicle[];
}

// Demo truck positions mapped to SVG coordinate space (India bounding box)
// Real lat/lng → SVG x,y via simple linear projection
const toSVG = (lat: number, lng: number) => {
    // India: lat 8-37, lng 68-97
    const x = ((lng - 68) / (97 - 68)) * 900 + 50;
    const y = ((37 - lat) / (37 - 8)) * 520 + 40;
    return { x, y };
};

const RISK_ZONES = [
    { name: 'NH48 High Risk Corridor', level: 'High' as const, lat1: 19.8, lng1: 73.2, lat2: 20.3, lng2: 74.1, color: '#ef4444' },
    { name: 'Pune–Nashik Belt', level: 'High' as const, lat1: 18.9, lng1: 73.5, lat2: 19.3, lng2: 74.2, color: '#ef4444' },
    { name: 'Kolkata–Kharagpur', level: 'High' as const, lat1: 22.1, lng1: 87.2, lat2: 22.7, lng2: 88.5, color: '#ef4444' },
    { name: 'Delhi NCR Zone', level: 'Medium' as const, lat1: 28.4, lng1: 76.7, lat2: 28.9, lng2: 77.4, color: '#f59e0b' },
    { name: 'Solapur Watch Zone', level: 'Medium' as const, lat1: 17.2, lng1: 75.5, lat2: 17.7, lng2: 76.1, color: '#f59e0b' },
    { name: 'Chennai–Blr Safe Corridor', level: 'Low' as const, lat1: 12.9, lng1: 77.5, lat2: 13.4, lng2: 80.1, color: '#10b981' },
    { name: 'Gujarat Safe Zone', level: 'Low' as const, lat1: 21.9, lng1: 72.3, lat2: 22.4, lng2: 73.0, color: '#10b981' },
];

// M5: Route paths for all 10 SEED_FLEET corridors
const DEMO_ROUTES = [
    { from: 'Chennai', to: 'Mumbai', points: [[13.08, 80.27], [15.34, 75.71], [17.38, 76.09], [18.52, 73.86], [19.07, 72.87]], color: '#dc2626' },
    { from: 'Mumbai', to: 'Ahmedabad', points: [[19.07, 72.87], [21.17, 72.83], [23.02, 72.57]], color: '#dc2626' },
    { from: 'Kolkata', to: 'Bhubaneswar', points: [[22.57, 88.36], [21.49, 86.73], [20.27, 85.84]], color: '#ef4444' },
    { from: 'Delhi', to: 'Ludhiana', points: [[28.70, 77.10], [29.38, 76.97], [30.90, 75.85]], color: '#ef4444' },
    { from: 'Surat', to: 'Ahmedabad', points: [[21.17, 72.83], [22.31, 72.14], [23.02, 72.57]], color: '#f59e0b' },
    { from: 'Mumbai', to: 'Hyderabad', points: [[19.07, 72.87], [18.00, 75.00], [17.38, 78.48]], color: '#f59e0b' },
    { from: 'Bangalore', to: 'Chennai', points: [[12.97, 77.59], [12.91, 79.13], [13.08, 80.27]], color: '#f59e0b' },
    { from: 'Delhi', to: 'Jaipur', points: [[28.70, 77.10], [28.00, 76.50], [26.91, 75.78]], color: '#10b981' },
    { from: 'Pune', to: 'Bangalore', points: [[18.52, 73.85], [15.85, 74.49], [12.97, 77.59]], color: '#10b981' },
    { from: 'Nagpur', to: 'Raipur', points: [[21.14, 79.08], [21.25, 81.63], [21.25, 81.63]], color: '#10b981' },
];

const riskColor = (level: string) =>
    level === 'Critical' ? '#dc2626' : level === 'High' ? '#ef4444' : level === 'Medium' ? '#f59e0b' : '#10b981';

export default function MapView({ fleet }: MapViewProps) {
    const displayFleet = fleet;
    const [activeVehicle, setActiveVehicle] = useState<string | null>(null);
    const [showZones, setShowZones] = useState(true);
    const [tick, setTick] = useState(0);
    const animRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

    // Animate truck positions slightly for realism
    useEffect(() => {
        animRef.current = setInterval(() => setTick(t => t + 1), 2000);
        return () => clearInterval(animRef.current);
    }, []);

    const activeV = displayFleet.find(v => v.info.id === activeVehicle);

    return (
        <div style={{ position: 'relative', height: '100%', width: '100%', overflow: 'hidden', borderRadius: '12px', background: '#f0f4f8' }}>

            {/* SVG Map */}
            <svg
                viewBox="0 0 1000 600"
                style={{ width: '100%', height: '100%', display: 'block' }}
                preserveAspectRatio="xMidYMid meet"
            >
                {/* Ocean / background */}
                <rect width="1000" height="600" fill="#dbeafe" rx="12" />

                {/* Grid lines */}
                {[...Array(10)].map((_, i) => (
                    <g key={i} opacity="0.15">
                        <line x1={i * 100} y1="0" x2={i * 100} y2="600" stroke="#3b82f6" strokeWidth="0.5" />
                        <line x1="0" y1={i * 60} x2="1000" y2={i * 60} stroke="#3b82f6" strokeWidth="0.5" />
                    </g>
                ))}

                {/* India SVG outline — simplified polygon */}
                <polygon
                    points={[
                        // Rough India outline in SVG coords (lat,lng → x,y)
                        [toSVG(37, 75).x, toSVG(37, 75).y],
                        [toSVG(35, 78).x, toSVG(35, 78).y],
                        [toSVG(32, 79).x, toSVG(32, 79).y],
                        [toSVG(30, 78).x, toSVG(30, 78).y],
                        [toSVG(28, 97).x, toSVG(28, 97).y],
                        [toSVG(24, 91).x, toSVG(24, 91).y],
                        [toSVG(22, 92).x, toSVG(22, 92).y],
                        [toSVG(23, 89).x, toSVG(23, 89).y],
                        [toSVG(21, 87).x, toSVG(21, 87).y],
                        [toSVG(20, 86).x, toSVG(20, 86).y],
                        [toSVG(14, 80).x, toSVG(14, 80).y],
                        [toSVG(10, 80).x, toSVG(10, 80).y],
                        [toSVG(8.1, 77.5).x, toSVG(8.1, 77.5).y],
                        [toSVG(9, 76.5).x, toSVG(9, 76.5).y],
                        [toSVG(11, 75).x, toSVG(11, 75).y],
                        [toSVG(14, 74).x, toSVG(14, 74).y],
                        [toSVG(17, 72.8).x, toSVG(17, 72.8).y],
                        [toSVG(19.5, 72.7).x, toSVG(19.5, 72.7).y],
                        [toSVG(22, 68.7).x, toSVG(22, 68.7).y],
                        [toSVG(24, 68).x, toSVG(24, 68).y],
                        [toSVG(27, 70).x, toSVG(27, 70).y],
                        [toSVG(28, 72).x, toSVG(28, 72).y],
                        [toSVG(30, 74).x, toSVG(30, 74).y],
                        [toSVG(32, 75).x, toSVG(32, 75).y],
                        [toSVG(34, 74).x, toSVG(34, 74).y],
                        [toSVG(36, 74.5).x, toSVG(36, 74.5).y],
                    ].map(([x, y]) => `${x},${y}`).join(' ')}
                    fill="#e8f0fe"
                    stroke="#93c5fd"
                    strokeWidth="1.5"
                />

                {/* Risk Zone Rectangles */}
                {showZones && RISK_ZONES.map(z => {
                    const p1 = toSVG(z.lat1, z.lng1);
                    const p2 = toSVG(z.lat2, z.lng2);
                    const x = Math.min(p1.x, p2.x);
                    const y = Math.min(p1.y, p2.y);
                    const w = Math.abs(p2.x - p1.x);
                    const h = Math.abs(p2.y - p1.y);
                    return (
                        <g key={z.name}>
                            <rect
                                x={x} y={y} width={w} height={h}
                                fill={z.color} fillOpacity={z.level === 'High' ? 0.18 : z.level === 'Medium' ? 0.13 : 0.1}
                                stroke={z.color} strokeWidth="1.5" strokeOpacity="0.6"
                                strokeDasharray={z.level === 'Low' ? '4 3' : 'none'}
                                rx="3"
                            />
                        </g>
                    );
                })}

                {/* Route Lines */}
                {DEMO_ROUTES.map(route => (
                    <polyline
                        key={route.from + route.to}
                        points={route.points.map(([lat, lng]) => {
                            const { x, y } = toSVG(lat, lng);
                            return `${x},${y}`;
                        }).join(' ')}
                        fill="none"
                        stroke={route.color}
                        strokeWidth="2"
                        strokeDasharray="8 4"
                        strokeOpacity="0.55"
                    />
                ))}

                {/* Truck Markers */}
                {displayFleet.map((vehicle, i) => {
                    const p = toSVG(vehicle.location.lat, vehicle.location.lng);
                    // Tiny drift animation
                    const dx = Math.sin(tick * 0.7 + i) * 2;
                    const dy = Math.cos(tick * 0.5 + i) * 1.5;
                    const cx = p.x + dx;
                    const cy = p.y + dy;
                    const col = riskColor(vehicle.risk.level);
                    const isActive = activeVehicle === vehicle.info.id;
                    const isHighRisk = vehicle.risk.level === 'High' || vehicle.risk.level === 'Critical';
                    return (
                        <g
                            key={vehicle.trip_id || `${vehicle.info.id}-${i}`}
                            onClick={() => setActiveVehicle(isActive ? null : vehicle.info.id)}
                            style={{ cursor: 'pointer' }}
                        >
                            {/* Pulsing ring for high-risk */}
                            {isHighRisk && (
                                <circle cx={cx} cy={cy} r={18 + (tick % 3) * 3} fill="none" stroke={col} strokeWidth="1" opacity={0.4 - (tick % 3) * 0.13} />
                            )}
                            {/* Shadow */}
                            <circle cx={cx + 1} cy={cy + 1} r={10} fill="rgba(0,0,0,0.12)" />
                            {/* Main dot */}
                            <circle
                                cx={cx} cy={cy} r={isActive ? 13 : 10}
                                fill={col}
                                stroke="white"
                                strokeWidth="2.5"
                                style={{ transition: 'r 0.2s ease' }}
                            />
                            {/* Inner dot */}
                            <circle cx={cx} cy={cy} r={3} fill="white" opacity="0.9" />
                            {/* Label */}
                            <rect x={cx + 13} y={cy - 11} width={vehicle.info.id.length * 6.5 + 8} height={18} rx="4" fill="white" opacity="0.95" />
                            <text x={cx + 17} y={cy + 1} fontSize="9" fontWeight="800" fill="#0f172a" fontFamily="system-ui">{vehicle.info.id}</text>
                        </g>
                    );
                })}

                {/* M4: All cities from SEED_FLEET routes */}
                {[
                    { name: 'Mumbai', lat: 19.07, lng: 72.87 },
                    { name: 'Delhi', lat: 28.70, lng: 77.10 },
                    { name: 'Chennai', lat: 13.08, lng: 80.27 },
                    { name: 'Bangalore', lat: 12.97, lng: 77.59 },
                    { name: 'Kolkata', lat: 22.57, lng: 88.36 },
                    { name: 'Hyderabad', lat: 17.38, lng: 78.48 },
                    { name: 'Pune', lat: 18.52, lng: 73.85 },
                    { name: 'Ahmedabad', lat: 23.02, lng: 72.57 },
                    { name: 'Jaipur', lat: 26.91, lng: 75.78 },
                    { name: 'Ludhiana', lat: 30.90, lng: 75.85 },
                    { name: 'Surat', lat: 21.17, lng: 72.83 },
                    { name: 'Nagpur', lat: 21.14, lng: 79.08 },
                    { name: 'Raipur', lat: 21.25, lng: 81.63 },
                    { name: 'Bhubaneswar', lat: 20.27, lng: 85.84 },
                ].map(city => {
                    const { x, y } = toSVG(city.lat, city.lng);
                    return (
                        <g key={city.name}>
                            <circle cx={x} cy={y} r={3.5} fill="#1e3a5f" opacity="0.5" />
                            <text x={x + 5} y={y + 4} fontSize="7.5" fill="#1e3a5f" opacity="0.7" fontFamily="system-ui" fontWeight="600">{city.name}</text>
                        </g>
                    );
                })}
            </svg>

            {/* M7: Popup positioned at right edge, not overlapping trucks */}
            {activeV && (
                <div style={{
                    position: 'absolute', top: 10, right: 145, // right side, clear of live badge
                    background: 'white', borderRadius: '12px', padding: '12px 18px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.12)', border: '1px solid rgba(226,232,240,1)',
                    minWidth: '220px', maxWidth: '260px', pointerEvents: 'none', zIndex: 20,
                    animation: 'fadeIn 0.2s ease',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <strong style={{ color: '#0f172a', fontSize: 14 }}>{activeV.info.id}</strong>
                        <span style={{
                            background: `${riskColor(activeV.risk.level)}15`,
                            color: riskColor(activeV.risk.level),
                            border: `1px solid ${riskColor(activeV.risk.level)}30`,
                            borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 800
                        }}>
                            {activeV.risk.level} — {activeV.risk.score}/100
                        </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#475569', fontWeight: 500 }}>{activeV.info.cargo}</div>
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{activeV.info.route}</div>
                    <div style={{ marginTop: 8, fontSize: 11, color: '#64748b', fontWeight: 600 }}>
                        {activeV.risk.reasons.map(r => `⚠ ${r}`).join(' · ')}
                    </div>
                </div>
            )}

            {/* M6: Legend with actual marker colors (not blue) */}
            <div style={{
                position: 'absolute', top: 10, left: 10, zIndex: 10,
                background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(8px)',
                borderRadius: 10, padding: '8px 12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.07)',
                border: '1px solid rgba(226,232,240,1)',
                fontSize: 10, minWidth: 140,
            }}>
                <div style={{ fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6, fontSize: 9 }}>Vehicle Risk</div>
                {[
                    { c: '#dc2626', l: 'Critical Risk' },
                    { c: '#ef4444', l: 'High Risk' },
                    { c: '#f59e0b', l: 'Medium Risk' },
                    { c: '#10b981', l: 'Low / Safe' },
                ].map(({ c, l }) => (
                    <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                        <div style={{ width: 10, height: 10, borderRadius: '50%', background: c, border: '2px solid white', boxShadow: `0 0 0 1px ${c}` }} />
                        <span style={{ color: '#334155', fontWeight: 600 }}>{l}</span>
                    </div>
                ))}
                <button
                    onClick={() => setShowZones(v => !v)}
                    style={{
                        marginTop: 6, padding: '3px 8px', background: showZones ? '#0284c7' : '#e2e8f0',
                        color: showZones ? 'white' : '#475569', border: 'none', borderRadius: 5,
                        fontSize: 9, fontWeight: 800, cursor: 'pointer', width: '100%', letterSpacing: 0.5
                    }}
                >
                    {showZones ? 'HIDE ZONES' : 'SHOW ZONES'}
                </button>
            </div>

            {/* Live indicator */}
            <div style={{
                position: 'absolute', top: 10, right: 10, zIndex: 10,
                background: 'rgba(255,255,255,0.95)', borderRadius: 999,
                padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 5,
                fontSize: 10, fontWeight: 800, color: '#ef4444',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                border: '1px solid rgba(226,232,240,1)'
            }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#ef4444', animation: 'pulse 1s infinite' }} />
                LIVE · {displayFleet.length} VEHICLES
            </div>

            {/* Click hint */}
            {!activeVehicle && (
                <div style={{
                    position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)',
                    background: 'rgba(255,255,255,0.9)', borderRadius: 999,
                    padding: '4px 14px', fontSize: 10, fontWeight: 600, color: '#64748b',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid rgba(226,232,240,1)'
                }}>
                    Click a vehicle dot for details
                </div>
            )}

            <style>{`
                @keyframes pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.3); }
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(8px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(0); }
                }
            `}</style>
        </div>
    );
}
