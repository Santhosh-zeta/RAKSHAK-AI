'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { FleetVehicle } from '@/services/apiClient';

// Helper to create custom colored markers
const createRiskIcon = (level: 'Low' | 'Medium' | 'High') => {
    let color = '#4ade80'; // Low risk - green
    if (level === 'Medium') color = '#fbbf24'; // yellow
    if (level === 'High') color = '#ef4444'; // red

    return L.divIcon({
        className: 'custom-fleet-marker',
        html: `
            <div style="
                width: 24px; 
                height: 24px; 
                background: ${color}; 
                border: 3px solid white; 
                border-radius: 50%; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div style="width: 8px; height: 8px; background: white; border-radius: 50%;"></div>
            </div>
            ${level === 'High' ? `<div style="position:absolute; top:-4px; left:-4px; right:-4px; bottom:-4px; border:2px solid ${color}; border-radius:50%; animation: pulse 1.5s infinite;"></div>` : ''}
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12]
    });
};

interface MapViewProps {
    fleet: FleetVehicle[];
}

export default function MapView({ fleet }: MapViewProps) {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted || fleet.length === 0) {
        return <div style={{ height: '100%', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading Map Engine...</div>;
    }

    // Calculate center based on the first truck or India's center
    const centerLat = fleet[0]?.location.lat || 20.5937;
    const centerLng = fleet[0]?.location.lng || 78.9629;

    return (
        <MapContainer
            center={[centerLat, centerLng]}
            zoom={5}
            style={{ height: '100%', width: '100%', borderRadius: '8px' }}
            zoomControl={false}
            attributionControl={false}
        >
            {/* Light themed map tiles */}
            <TileLayer
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            />

            {fleet.map((vehicle) => (
                <Marker
                    key={vehicle.info.id}
                    position={[vehicle.location.lat, vehicle.location.lng]}
                    icon={createRiskIcon(vehicle.risk.level)}
                >
                    <Popup>
                        <div style={{ padding: '4px' }}>
                            <strong style={{ fontSize: '14px', color: '#1e293b' }}>{vehicle.info.id}</strong><br />
                            <span style={{ color: '#64748b', fontSize: '12px' }}>{vehicle.info.cargo}</span><br />
                            <div style={{ marginTop: '4px', fontWeight: 'bold', color: vehicle.risk.level === 'High' ? '#ef4444' : vehicle.risk.level === 'Medium' ? '#fbbf24' : '#4ade80' }}>
                                Risk: {vehicle.risk.level} ({vehicle.risk.score}%)
                            </div>
                        </div>
                    </Popup>
                </Marker>
            ))}
        </MapContainer>
    );
}
