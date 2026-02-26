'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';

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

export default function GoogleMapComponent({
    markers = [],
    center = { lat: 28.6139, lng: 77.2090 }, // Default: Delhi
    zoom = 7,
    height = '480px',
    onMarkerClick,
    polyline,
    dangerZones = [],
}: GoogleMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<google.maps.Map | null>(null);
    const markersRef = useRef<google.maps.Marker[]>([]);
    const polylineRef = useRef<google.maps.Polyline | null>(null);
    const dangerMarkersRef = useRef<google.maps.Marker[]>([]);
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState(false);

    // Load Google Maps
    useEffect(() => {
        if (!API_KEY) {
            setError(true);
            return;
        }

        const loader = new Loader({
            apiKey: API_KEY,
            version: 'weekly',
            libraries: ['places'],
        });

        // @ts-ignore
        loader.importLibrary('maps').then(() => {
            if (!mapRef.current || mapInstanceRef.current) return;

            const map = new google.maps.Map(mapRef.current, {
                center,
                zoom,
                styles: [
                    { elementType: 'geometry', stylers: [{ color: '#1e293b' }] },
                    { elementType: 'labels.text.stroke', stylers: [{ color: '#0f172a' }] },
                    { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
                    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#334155' }] },
                    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#1e3a5f' }] },
                    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0f2442' }] },
                    { featureType: 'poi', stylers: [{ visibility: 'off' }] },
                    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
                ],
                disableDefaultUI: false,
                streetViewControl: false,
                mapTypeControl: false,
                fullscreenControl: true,
            });

            mapInstanceRef.current = map;
            setLoaded(true);
        }).catch(() => setError(true));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Update markers when data changes
    useEffect(() => {
        if (!loaded || !mapInstanceRef.current) return;
        const map = mapInstanceRef.current;

        // Clear old markers
        markersRef.current.forEach(m => m.setMap(null));
        markersRef.current = [];

        const infoWindow = new google.maps.InfoWindow();

        markers.forEach(marker => {
            const color = RISK_COLORS[marker.riskLevel] || '#64748b';
            const svgMarker = {
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: color,
                fillOpacity: 0.9,
                strokeWeight: 2,
                strokeColor: '#fff',
                scale: marker.riskLevel === 'Critical' ? 10 : marker.riskLevel === 'High' ? 9 : 8,
            };

            const gMarker = new google.maps.Marker({
                position: { lat: marker.lat, lng: marker.lng },
                map,
                title: marker.title,
                icon: svgMarker,
                animation: marker.riskLevel === 'Critical' ? google.maps.Animation.BOUNCE : undefined,
            });

            gMarker.addListener('click', () => {
                infoWindow.setContent(`
                    <div style="font-family:Inter,sans-serif;min-width:180px;padding:4px">
                        <div style="font-weight:800;font-size:0.9rem;margin-bottom:6px">${marker.truckId || marker.title}</div>
                        <div style="display:flex;gap:6px;align-items:center;margin-bottom:4px">
                            <span style="background:${color};color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;font-weight:700">${marker.riskLevel}</span>
                            <span style="font-size:0.8rem;color:#64748b">Risk: ${marker.riskScore ?? '—'}/100</span>
                        </div>
                        ${marker.route ? `<div style="font-size:0.78rem;color:#475569">📍 ${marker.route}</div>` : ''}
                        ${marker.status ? `<div style="font-size:0.78rem;color:#475569;margin-top:2px">Status: ${marker.status}</div>` : ''}
                        <div style="font-size:0.72rem;color:#94a3b8;margin-top:6px">${marker.lat.toFixed(4)}°N, ${marker.lng.toFixed(4)}°E</div>
                    </div>
                `);
                infoWindow.open(map, gMarker);
                if (onMarkerClick) onMarkerClick(marker);
            });

            markersRef.current.push(gMarker);
        });

        // Auto-fit bounds if multiple markers
        if (markers.length > 1) {
            const bounds = new google.maps.LatLngBounds();
            markers.forEach(m => bounds.extend({ lat: m.lat, lng: m.lng }));
            map.fitBounds(bounds, 60);
        }
    }, [loaded, markers, onMarkerClick]);

    // Draw route polyline
    useEffect(() => {
        if (!loaded || !mapInstanceRef.current) return;
        if (polylineRef.current) polylineRef.current.setMap(null);

        if (polyline && polyline.length > 1) {
            polylineRef.current = new google.maps.Polyline({
                path: polyline,
                geodesic: true,
                strokeColor: '#3b82f6',
                strokeOpacity: 0.85,
                strokeWeight: 4,
                map: mapInstanceRef.current,
            });
        }
    }, [loaded, polyline]);

    // Draw danger zone markers
    useEffect(() => {
        if (!loaded || !mapInstanceRef.current) return;
        dangerMarkersRef.current.forEach(m => m.setMap(null));
        dangerMarkersRef.current = [];

        dangerZones.forEach(zone => {
            const dMarker = new google.maps.Marker({
                position: { lat: zone.lat, lng: zone.lng },
                map: mapInstanceRef.current!,
                title: zone.name,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: '#ef4444',
                    fillOpacity: 0.3,
                    strokeColor: '#ef4444',
                    strokeWeight: 2,
                    scale: 16,
                },
                label: { text: '⚠', color: '#ef4444', fontSize: '16px' },
            });
            dangerMarkersRef.current.push(dMarker);
        });
    }, [loaded, dangerZones]);

    if (error && !API_KEY) {
        return (
            <div style={{
                height, background: '#1e293b', borderRadius: 12,
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', gap: 12, color: '#64748b',
                border: '1px dashed rgba(255,255,255,0.1)',
            }}>
                <div style={{ fontSize: '2rem' }}>🗺️</div>
                <div style={{ fontWeight: 700, color: '#94a3b8' }}>Google Maps not configured</div>
                <div style={{ fontSize: '0.8rem', textAlign: 'center', maxWidth: 280 }}>
                    Add <code style={{ background: '#0f172a', padding: '2px 6px', borderRadius: 4 }}>NEXT_PUBLIC_GOOGLE_MAPS_KEY</code> to your <code style={{ background: '#0f172a', padding: '2px 6px', borderRadius: 4 }}>.env.local</code> file
                </div>
            </div>
        );
    }

    return (
        <div style={{ position: 'relative', height, borderRadius: 12, overflow: 'hidden' }}>
            <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
            {!loaded && !error && (
                <div style={{
                    position: 'absolute', inset: 0, background: '#1e293b',
                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', gap: 12, color: '#64748b',
                }}>
                    <div style={{
                        width: 40, height: 40, borderRadius: '50%',
                        border: '3px solid rgba(59,130,246,0.2)',
                        borderTop: '3px solid #3b82f6',
                        animation: 'spin 1s linear infinite',
                    }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Loading map...</span>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
            )}
        </div>
    );
}
