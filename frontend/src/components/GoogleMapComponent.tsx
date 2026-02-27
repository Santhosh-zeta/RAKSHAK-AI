'use client';

/**
 * GoogleMapComponent — RAKSHAK AI
 * Robust Google Maps integration using the JS API Loader with singleton pattern.
 * Shows truck markers (colour-coded by risk), route polylines, and danger zones.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface MapMarker {
    lat: number;
    lng: number;
    title: string;
    riskLevel: 'Low' | 'Medium' | 'High' | 'Critical';
    riskScore?: number;
    truckId?: string;
    status?: string;
    route?: string;
    onClick?: () => void;
}

interface GoogleMapProps {
    markers?: MapMarker[];
    center?: { lat: number; lng: number };
    zoom?: number;
    height?: string;
    onMarkerClick?: (marker: MapMarker) => void;
    polyline?: { lat: number; lng: number }[];
    dangerZones?: { lat: number; lng: number; name: string }[];
}

const RISK_COLORS: Record<string, string> = {
    Low: '#10b981',
    Medium: '#f59e0b',
    High: '#f97316',
    Critical: '#ef4444',
};

const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || '';

// ─── Singleton loader: ensures the SDK script only injects once ───────────────

let _sdkPromise: Promise<void> | null = null;

function loadGoogleMapsSDK(): Promise<void> {
    if (_sdkPromise) return _sdkPromise;

    _sdkPromise = new Promise<void>((resolve, reject) => {
        // Already loaded (e.g., HMR reload)
        if (typeof window !== 'undefined' && (window as any).google?.maps) {
            resolve();
            return;
        }

        const callbackName = '__rakshak_maps_ready__';
        (window as any)[callbackName] = () => {
            delete (window as any)[callbackName];
            resolve();
        };

        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${API_KEY}&libraries=places,geometry&callback=${callbackName}&loading=async`;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
            _sdkPromise = null; // allow retry
            reject(new Error('Google Maps script failed to load'));
        };
        document.head.appendChild(script);
    });

    return _sdkPromise;
}

// ─── Map styles ───────────────────────────────────────────────────────────────

const MAP_STYLES: google.maps.MapTypeStyle[] = [
    { elementType: 'geometry', stylers: [{ color: '#1e293b' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#0f172a' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#334155' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#1e3a5f' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0f2442' }] },
    { featureType: 'poi', stylers: [{ visibility: 'off' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
    { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#475569' }] },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function GoogleMapComponent({
    markers = [],
    center = { lat: 22.5, lng: 80.0 }, // India centre
    zoom = 5,
    height = '480px',
    onMarkerClick,
    polyline,
    dangerZones = [],
}: GoogleMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstance = useRef<google.maps.Map | null>(null);
    const gMarkers = useRef<google.maps.Marker[]>([]);
    const gPolyline = useRef<google.maps.Polyline | null>(null);
    const gDangerMarks = useRef<google.maps.Marker[]>([]);
    const infoWindow = useRef<google.maps.InfoWindow | null>(null);

    const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
    const [errorMsg, setErrorMsg] = useState('');

    // ── 1. Load SDK once ─────────────────────────────────────────────────────

    useEffect(() => {
        if (!API_KEY) {
            setState('error');
            setErrorMsg('NEXT_PUBLIC_GOOGLE_MAPS_KEY not set in .env.local');
            return;
        }

        // Already initialised in this render cycle
        if (mapInstance.current) {
            setState('ready');
            return;
        }

        loadGoogleMapsSDK()
            .then(() => {
                if (!mapRef.current) return;

                const map = new google.maps.Map(mapRef.current, {
                    center,
                    zoom,
                    styles: MAP_STYLES,
                    disableDefaultUI: false,
                    streetViewControl: false,
                    mapTypeControl: false,
                    fullscreenControl: true,
                    zoomControl: true,
                    gestureHandling: 'greedy',
                });

                mapInstance.current = map;
                infoWindow.current = new google.maps.InfoWindow();
                setState('ready');
            })
            .catch(err => {
                console.error('[RAKSHAK] Maps load error:', err);
                setState('error');
                setErrorMsg(err.message || 'Failed to load Google Maps');
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── 2. Update markers ─────────────────────────────────────────────────────

    useEffect(() => {
        if (state !== 'ready' || !mapInstance.current) return;
        const map = mapInstance.current;
        const iw = infoWindow.current!;

        // Clear previous
        gMarkers.current.forEach(m => m.setMap(null));
        gMarkers.current = [];

        markers.forEach(marker => {
            const color = RISK_COLORS[marker.riskLevel] || '#64748b';
            const scale = marker.riskLevel === 'Critical' ? 11 : marker.riskLevel === 'High' ? 10 : 8;

            const gm = new google.maps.Marker({
                position: { lat: marker.lat, lng: marker.lng },
                map,
                title: marker.title,
                animation: marker.riskLevel === 'Critical' ? google.maps.Animation.BOUNCE : undefined,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: color,
                    fillOpacity: 0.9,
                    strokeColor: '#ffffff',
                    strokeWeight: 2,
                    scale,
                },
            });

            gm.addListener('click', () => {
                iw.setContent(`
                    <div style="font-family:Inter,sans-serif;min-width:190px;padding:4px">
                        <div style="font-weight:800;font-size:0.9rem;margin-bottom:6px;color:#0f172a">${marker.truckId || marker.title}</div>
                        <div style="display:flex;gap:6px;align-items:center;margin-bottom:4px">
                            <span style="background:${color};color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;font-weight:700">${marker.riskLevel}</span>
                            <span style="font-size:0.8rem;color:#64748b">Risk: ${marker.riskScore ?? '—'}/100</span>
                        </div>
                        ${marker.route ? `<div style="font-size:0.78rem;color:#475569">📍 ${marker.route}</div>` : ''}
                        ${marker.status ? `<div style="font-size:0.78rem;color:#475569;margin-top:2px">Status: ${marker.status}</div>` : ''}
                        <div style="font-size:0.72rem;color:#94a3b8;margin-top:6px">${marker.lat.toFixed(4)}°N, ${marker.lng.toFixed(4)}°E</div>
                    </div>
                `);
                iw.open(map, gm);
                if (onMarkerClick) onMarkerClick(marker);
            });

            gMarkers.current.push(gm);
        });

        // Auto-fit bounds
        if (markers.length > 1) {
            const bounds = new google.maps.LatLngBounds();
            markers.forEach(m => bounds.extend({ lat: m.lat, lng: m.lng }));
            map.fitBounds(bounds, { top: 60, right: 40, bottom: 40, left: 40 });
        } else if (markers.length === 1) {
            map.panTo({ lat: markers[0].lat, lng: markers[0].lng });
        }
    }, [state, markers, onMarkerClick]);

    // ── 3. Draw polyline ──────────────────────────────────────────────────────

    useEffect(() => {
        if (state !== 'ready' || !mapInstance.current) return;
        if (gPolyline.current) gPolyline.current.setMap(null);

        if (polyline && polyline.length > 1) {
            gPolyline.current = new google.maps.Polyline({
                path: polyline,
                geodesic: true,
                strokeColor: '#3b82f6',
                strokeOpacity: 0.9,
                strokeWeight: 4,
                map: mapInstance.current,
            });
        }
    }, [state, polyline]);

    // ── 4. Draw danger zones ──────────────────────────────────────────────────

    useEffect(() => {
        if (state !== 'ready' || !mapInstance.current) return;
        gDangerMarks.current.forEach(m => m.setMap(null));
        gDangerMarks.current = [];

        dangerZones.forEach(zone => {
            const dm = new google.maps.Marker({
                position: { lat: zone.lat, lng: zone.lng },
                map: mapInstance.current!,
                title: zone.name,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: '#ef4444',
                    fillOpacity: 0.25,
                    strokeColor: '#ef4444',
                    strokeWeight: 2,
                    scale: 18,
                },
                label: { text: '⚠', color: '#ef4444', fontSize: '16px' },
            });
            gDangerMarks.current.push(dm);
        });
    }, [state, dangerZones]);

    // ── Render ────────────────────────────────────────────────────────────────

    if (state === 'error') {
        return (
            <div style={{
                height, background: '#1e293b', borderRadius: 12,
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', gap: 12, color: '#64748b',
                border: '1px dashed rgba(255,255,255,0.1)',
            }}>
                <div style={{ fontSize: '2.5rem' }}>🗺️</div>
                <div style={{ fontWeight: 700, color: '#94a3b8', fontSize: '0.95rem' }}>
                    {API_KEY ? 'Maps API Error' : 'Google Maps not configured'}
                </div>
                <div style={{ fontSize: '0.78rem', textAlign: 'center', maxWidth: 300, lineHeight: 1.6, color: '#64748b' }}>
                    {errorMsg || 'Check the browser console for details.'}
                </div>
            </div>
        );
    }

    return (
        <div style={{ position: 'relative', height, borderRadius: 12, overflow: 'hidden' }}>
            {/* Map container */}
            <div ref={mapRef} style={{ width: '100%', height: '100%' }} />

            {/* Loading overlay */}
            {state === 'loading' && (
                <div style={{
                    position: 'absolute', inset: 0, background: '#1e293b',
                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', gap: 14, color: '#64748b',
                }}>
                    <div style={{
                        width: 42, height: 42, borderRadius: '50%',
                        border: '3px solid rgba(59,130,246,0.15)',
                        borderTop: '3px solid #3b82f6',
                        animation: 'spin 0.9s linear infinite',
                    }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Connecting to Google Maps...</span>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
            )}
        </div>
    );
}
