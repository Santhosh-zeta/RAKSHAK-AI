// This service connects to the Rakshak AI Django backend
// Base URL handles the /api suffix where the Django routers are mounted
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Helper to disable mocks when pushing to production or fully integrated
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

// Types
export interface TruckInfo {
    id: string;      // maps to truck.license_plate
    cargo: string;   // maps to truck.cargo_type
    value: number;   // maps to truck.cargo_value
    route: string;   // maps to start_location_name -> destination_name
}

export interface RiskScore {
    score: number; // 0-100
    level: 'Low' | 'Medium' | 'High' | 'Critical';
    reasons: string[];
}

export interface LocationData {
    lat: number;
    lng: number;
}

export interface Alert {
    id: string;
    time: string;
    message: string;
    level: 'Low' | 'Medium' | 'High' | 'Critical';
    truckId?: string; // maps to trip.truck.license_plate
}

// Fleet Types
export interface FleetVehicle {
    trip_id: string;
    info: TruckInfo;
    risk: RiskScore;
    location: LocationData;
    status: string; // 'Scheduled' | 'In-Transit' | 'Alert'
}

// --- MOCK DATA FALLBACK ---
const MOCK_FLEET: FleetVehicle[] = [
    {
        trip_id: 'mock-uuid-1',
        info: { id: 'TR102', cargo: 'Electronics', value: 1500000, route: 'Chennai → Mumbai' },
        risk: { score: 72, level: 'High', reasons: ['Night travel', 'High risk zone'] },
        location: { lat: 19.0760, lng: 72.8777 },
        status: 'Alert'
    },
    {
        trip_id: 'mock-uuid-2',
        info: { id: 'TR205', cargo: 'Pharmaceuticals', value: 3200000, route: 'Delhi → Jaipur' },
        risk: { score: 15, level: 'Low', reasons: ['Daylight', 'Secure Highway'] },
        location: { lat: 28.7041, lng: 77.1025 },
        status: 'In Transit'
    },
    {
        trip_id: 'mock-uuid-3',
        info: { id: 'TR318', cargo: 'Textiles', value: 500000, route: 'Surat → Ahmedabad' },
        risk: { score: 55, level: 'Medium', reasons: ['Weather conditions', 'Unscheduled stop'] },
        location: { lat: 21.1702, lng: 72.8311 },
        status: 'Alert'
    },
    {
        trip_id: 'mock-uuid-4',
        info: { id: 'TR440', cargo: 'Automotive Parts', value: 850000, route: 'Pune → Bangalore' },
        risk: { score: 22, level: 'Low', reasons: ['Routine transit'] },
        location: { lat: 18.5204, lng: 73.8567 },
        status: 'In Transit'
    }
];

const MOCK_ALERTS: Alert[] = [
    { id: '1', truckId: 'TR102', time: '10:30 PM', message: 'Truck stopped unusually', level: 'Medium' },
    { id: '2', truckId: 'TR102', time: '10:35 PM', message: 'High risk zone entered', level: 'High' },
    { id: '3', truckId: 'TR102', time: '10:40 PM', message: 'Person detected near cargo', level: 'Critical' },
    { id: '4', truckId: 'TR318', time: '09:15 PM', message: 'Route deviation detected', level: 'Medium' },
];

// --- API CLIENT FUNCTIONS ---

/**
 * Fetches all active Trips from the Django backend and maps them to FleetVehicle format
 */
export async function getFleetData(): Promise<FleetVehicle[]> {
    if (USE_MOCK) return MOCK_FLEET;

    try {
        // Fetch all trips
        const tripRes = await fetch(`${API_BASE_URL}/trips/`);
        if (!tripRes.ok) throw new Error('Failed to fetch trips');
        const trips = await tripRes.json();

        const fleet: FleetVehicle[] = [];

        for (const trip of trips) {
            // For each trip, we hit the dashboard action to get the live risk and location
            // If fetching 100 trips, this N+1 structure should be optimized on the Django side in the future
            const dsRes = await fetch(`${API_BASE_URL}/trips/${trip.trip_id}/dashboard/`);
            if (!dsRes.ok) continue;

            const dashboard = await dsRes.json();

            // Map GPS details from dashboard payload, or use the start_location_coords 
            let lat = 20.5937;
            let lng = 78.9629;
            if (dashboard.latest_location) {
                lat = floatOrDefault(dashboard.latest_location.latitude, lat);
                lng = floatOrDefault(dashboard.latest_location.longitude, lng);
            } else if (trip.start_location_coords) {
                try {
                    // Django is storing start coords as 'lat,lng' string or tuple string based on service 
                    const parts = String(trip.start_location_coords).replace('[', '').replace(']', '').split(',');
                    if (parts.length >= 2) {
                        lat = floatOrDefault(parts[0], lat);
                        lng = floatOrDefault(parts[1], lng);
                    }
                } catch { /* ignore parse error */ }
            }

            // Reason strings from recent alerts
            const reasons = (dashboard.recent_alerts || []).map((a: any) => a.type);

            const score = floatOrDefault(dashboard.current_risk_score, 0);
            let riskLevel: 'Low' | 'Medium' | 'High' | 'Critical' = 'Low';
            if (score >= 80) riskLevel = 'Critical';
            else if (score >= 60) riskLevel = 'High';
            else if (score >= 40) riskLevel = 'Medium';

            fleet.push({
                trip_id: trip.trip_id,
                info: {
                    id: trip.truck?.license_plate || 'Unassigned',
                    cargo: trip.truck?.cargo_type || 'Unknown Cargo',
                    value: floatOrDefault(trip.truck?.cargo_value, 0),
                    route: `${trip.start_location_name} → ${trip.destination_name}`
                },
                risk: {
                    score: Math.round(score),
                    level: riskLevel,
                    reasons: reasons.length ? [...new Set(reasons)] as string[] : ['Baseline transit']
                },
                location: { lat, lng },
                status: trip.status
            });
        }

        return fleet;

    } catch (e) {
        console.warn('Backend API failed to connect. Ensure python manage.py runserver is active.', e);
        return [];
    }
}

/**
 * Fetches all global alerts from the Django API
 */
export async function getAlerts(): Promise<Alert[]> {
    if (USE_MOCK) return MOCK_ALERTS;

    try {
        const res = await fetch(`${API_BASE_URL}/alerts/`);
        if (!res.ok) throw new Error('API failed');
        const data = await res.json();

        // Map Django Alert models to frontend UI Alert interfaces
        return data.map((d: any) => {
            const date = new Date(d.timestamp);
            const formattedTime = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return {
                id: d.alert_id,
                truckId: d.trip?.truck?.license_plate || 'TRK-???',
                time: formattedTime,
                message: d.description,
                level: d.severity
            };
        }).sort((a: any, b: any) => (a.time > b.time ? -1 : 1)); // Descending sort

    } catch (e) {
        return [];
    }
}

/**
 * Triggers the hackathon Simulation endpoint on the Django backend 
 * to instantly spawn artificial alerts on a specific trip
 */
export async function triggerSimulation(tripId: string): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/simulate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trip_id: tripId })
        });
        return res.ok;
    } catch (e) {
        return false;
    }
}

// Utility mapper
function floatOrDefault(val: any, defaultVal: number): number {
    const parsed = parseFloat(val);
    return isNaN(parsed) ? defaultVal : parsed;
}

export async function getVisionDetection(): Promise<{ active: boolean, log: string[] }> {
    if (USE_MOCK) return { active: true, log: ['Person detected - Confidence 0.92'] };
    try {
        const res = await fetch(`${API_BASE_URL}/detect`);
        if (!res.ok) throw new Error('API failed');
        return await res.json();
    } catch (e) {
        return { active: true, log: ['Person detected - Confidence 0.92'] };
    }
}
