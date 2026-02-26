// RAKSHAK AI — API Client
// Connects to Django backend automatically.
// If backend is unreachable, falls back to comprehensive seed data (great for demos).

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TruckInfo {
    id: string;
    cargo: string;
    value: number;
    route: string;
}

export interface RiskScore {
    score: number;
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
    truckId?: string;
    aiExplanation?: string;
    riskScore?: number;
    type?: string;
}

// Extended alert with guaranteed AI fields (used in Alerts page)
export interface EnhancedAlert extends Alert {
    aiExplanation: string;
    riskScore: number;
    type: string;
}

export interface FleetVehicle {
    trip_id: string;
    info: TruckInfo;
    risk: RiskScore;
    location: LocationData;
    status: string;
}

// ─── SEED / DEMO DATA ────────────────────────────────────────────────────────
// 10 trucks covering real Indian logistics corridors with varied risk levels

export const SEED_FLEET: FleetVehicle[] = [
    {
        trip_id: 'trip-001',
        info: { id: 'TR-102', cargo: 'Electronics', value: 1500000, route: 'Chennai → Mumbai' },
        risk: { score: 82, level: 'Critical', reasons: ['Night transit', 'High-theft zone', 'Stopped 47 min'] },
        location: { lat: 19.07, lng: 72.87 },
        status: 'Alert'
    },
    {
        trip_id: 'trip-002',
        info: { id: 'TR-205', cargo: 'Pharmaceuticals', value: 3200000, route: 'Delhi → Jaipur' },
        risk: { score: 14, level: 'Low', reasons: ['Daylight hours', 'Green corridor', 'Driver: 12 yrs exp'] },
        location: { lat: 27.26, lng: 76.58 },
        status: 'In Transit'
    },
    {
        trip_id: 'trip-003',
        info: { id: 'TR-318', cargo: 'Textiles', value: 520000, route: 'Surat → Ahmedabad' },
        risk: { score: 58, level: 'Medium', reasons: ['Unscheduled stop 22 min', 'Unfamiliar route segment'] },
        location: { lat: 22.31, lng: 72.14 },
        status: 'Alert'
    },
    {
        trip_id: 'trip-004',
        info: { id: 'TR-440', cargo: 'Automotive Parts', value: 850000, route: 'Pune → Bangalore' },
        risk: { score: 20, level: 'Low', reasons: ['Routine transit', 'Daylight', 'On-schedule'] },
        location: { lat: 15.85, lng: 74.49 },
        status: 'In Transit'
    },
    {
        trip_id: 'trip-005',
        info: { id: 'TR-557', cargo: 'Steel Coils', value: 420000, route: 'Kolkata → Bhubaneswar' },
        risk: { score: 71, level: 'High', reasons: ['NH16 high-theft stretch', 'Night travel', 'Low driver rating'] },
        location: { lat: 22.32, lng: 87.38 },
        status: 'Alert'
    },
    {
        trip_id: 'trip-006',
        info: { id: 'TR-613', cargo: 'FMCG Goods', value: 680000, route: 'Mumbai → Hyderabad' },
        risk: { score: 46, level: 'Medium', reasons: ['Solapur district risk zone', 'Moderate traffic'] },
        location: { lat: 17.68, lng: 76.08 },
        status: 'In Transit'
    },
    {
        trip_id: 'trip-007',
        info: { id: 'TR-721', cargo: 'Luxury Apparel', value: 2800000, route: 'Delhi → Ludhiana' },
        risk: { score: 63, level: 'High', reasons: ['High cargo value', 'Night dispatch', 'Route deviation +8 km'] },
        location: { lat: 29.52, lng: 76.98 },
        status: 'Alert'
    },
    {
        trip_id: 'trip-008',
        info: { id: 'TR-834', cargo: 'Cement', value: 180000, route: 'Nagpur → Raipur' },
        risk: { score: 11, level: 'Low', reasons: ['Low-value cargo', 'Daytime', 'State highway'] },
        location: { lat: 21.35, lng: 79.55 },
        status: 'In Transit'
    },
    {
        trip_id: 'trip-009',
        info: { id: 'TR-919', cargo: 'Mobile Phones', value: 4200000, route: 'Bangalore → Chennai' },
        risk: { score: 34, level: 'Medium', reasons: ['High cargo value', 'Speed anomaly detected'] },
        location: { lat: 13.08, lng: 80.27 },
        status: 'In Transit'
    },
    {
        trip_id: 'trip-010',
        info: { id: 'TR-1044', cargo: 'Medical Equipment', value: 5600000, route: 'Mumbai → Ahmedabad' },
        risk: { score: 88, level: 'Critical', reasons: ['Person near cargo hatch', 'YOLO detection: 2 suspects', 'GPS signal lost 3 min'] },
        location: { lat: 21.90, lng: 72.30 },
        status: 'Alert'
    },
];

export const SEED_ALERTS: Alert[] = [
    {
        id: 'alrt-001', truckId: 'TR-1044', time: '10:52 PM', level: 'Critical',
        message: 'YOLO Vision: 2 persons detected loitering near cargo hatch — rear-door proximity alert',
        aiExplanation: 'Explainability Engine: Dual-person loitering event confirmed by DeepSORT tracker over 47 seconds. Behavioral anomaly index 0.94. Immediate intervention required.',
        riskScore: 88, type: 'Vision'
    },
    {
        id: 'alrt-002', truckId: 'TR-102', time: '10:40 PM', level: 'Critical',
        message: 'Truck stopped for 47 minutes in unlit area — no scheduled rest point nearby',
        aiExplanation: 'Explainability Engine: Stop duration 4.7x above baseline. Digital Twin deviation critical. Location cross-referenced with 3 prior theft incidents in 2024.',
        riskScore: 82, type: 'Behavior'
    },
    {
        id: 'alrt-003', truckId: 'TR-721', time: '10:35 PM', level: 'High',
        message: 'Route deviation detected — 8.2 km off planned NH44 trajectory',
        aiExplanation: 'Explainability Engine: Geofence breach confirmed. Alternate route has no registered checkpoints. Driver has not acknowledged deviation via app.',
        riskScore: 72, type: 'Route'
    },
    {
        id: 'alrt-004', truckId: 'TR-557', time: '10:15 PM', level: 'High',
        message: 'NH16 high-theft corridor entered — solo night travel with high-value steel coils',
        aiExplanation: 'Explainability Engine: Route Risk Agent flags this stretch: 7 cargo thefts in last 90 days. Night + low driver score + corridor risk compounds probability to 71%.',
        riskScore: 71, type: 'Route'
    },
    {
        id: 'alrt-005', truckId: 'TR-318', time: '09:22 PM', level: 'Medium',
        message: 'Unscheduled halt for 22 minutes — engine running, location: Surat Industrial Ring Road',
        aiExplanation: 'Explainability Engine: Moderate risk — unplanned stop with engine idle. No visual confirmation yet. Digital Twin flagged this stop as 2.7x above normal duration.',
        riskScore: 58, type: 'Behavior'
    },
    {
        id: 'alrt-006', truckId: 'TR-613', time: '09:05 PM', level: 'Medium',
        message: 'Entering Solapur medium-risk zone — speed reduced to 22 km/h on highway',
        aiExplanation: 'Explainability Engine: Speed anomaly below 30 km/h on NH65. Area classified as Medium risk by Route Intelligence. Monitoring active.',
        riskScore: 48, type: 'Route'
    },
    {
        id: 'alrt-007', truckId: 'TR-919', time: '08:50 PM', level: 'Medium',
        message: 'Cargo weight sensor anomaly — 3.2% deviation from loaded weight baseline',
        aiExplanation: 'Explainability Engine: IoT weight sensor flagged a 3.2% decrease from baseline scan. Could indicate partial cargo removal. Monitoring continues.',
        riskScore: 34, type: 'IoT'
    },
    {
        id: 'alrt-008', truckId: 'TR-205', time: '08:30 PM', level: 'Low',
        message: 'Trip commenced from Delhi depot — all pre-journey checks passed',
        aiExplanation: 'Explainability Engine: Pre-departure RFID seal verified. Route risk score 14/100. Driver experience 12 years. All parameters nominal.',
        riskScore: 14, type: 'System'
    },
    {
        id: 'alrt-009', truckId: 'TR-440', time: '07:45 PM', level: 'Low',
        message: 'Waypoint Kolhapur checkpoint passed — ETA Bangalore on schedule',
        aiExplanation: 'Explainability Engine: Routine checkpoint scan passed. Risk score remains low at 20/100. No anomalies detected in cargo or behavior.',
        riskScore: 20, type: 'System'
    },
    {
        id: 'alrt-010', truckId: 'TR-834', time: '07:15 PM', level: 'Low',
        message: 'Refuelling stop at Wardha Highway Petrol — duration 11 minutes (expected)',
        aiExplanation: 'Explainability Engine: Planned refuelling event. Stop duration within acceptable range (8–15 min). No behavioral anomalies detected.',
        riskScore: 11, type: 'System'
    },
    {
        id: 'alrt-011', truckId: 'TR-1044', time: '10:48 PM', level: 'Critical',
        message: 'GPS signal lost for 3 minutes then restored — suspected signal jamming attempt',
        aiExplanation: 'Explainability Engine: GPS blackout of 187 seconds in open-sky region is consistent with active jamming devices used in organized cargo theft operations. Cross-referencing with VSAT logs.',
        riskScore: 91, type: 'IoT'
    },
    {
        id: 'alrt-012', truckId: 'TR-102', time: '10:32 PM', level: 'High',
        message: 'Driver fatigue indicator — no steering wheel movement for 18 seconds at 60 km/h',
        aiExplanation: 'Explainability Engine: Steering inactivity detected via CAN bus telemetry. Pattern consistent with microsleep event. Driver alert system activated.',
        riskScore: 68, type: 'Behavior'
    },
];

// ─── API FUNCTIONS ────────────────────────────────────────────────────────────

export async function getFleetData(): Promise<FleetVehicle[]> {
    if (USE_MOCK) return SEED_FLEET;

    try {
        const tripRes = await fetch(`${API_BASE_URL}/trips/`);
        if (!tripRes.ok) throw new Error('trips fetch failed');
        const trips = await tripRes.json();

        const fleet: FleetVehicle[] = [];

        for (const trip of trips) {
            const dsRes = await fetch(`${API_BASE_URL}/trips/${trip.trip_id}/dashboard/`);
            if (!dsRes.ok) continue;
            const dashboard = await dsRes.json();

            let lat = 20.5937, lng = 78.9629;
            if (dashboard.latest_location) {
                lat = floatOrDefault(dashboard.latest_location.latitude, lat);
                lng = floatOrDefault(dashboard.latest_location.longitude, lng);
            } else if (trip.start_location_coords) {
                try {
                    const parts = String(trip.start_location_coords).replace('[', '').replace(']', '').split(',');
                    if (parts.length >= 2) { lat = floatOrDefault(parts[0], lat); lng = floatOrDefault(parts[1], lng); }
                } catch { /* ignore */ }
            }

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
                    cargo: trip.truck?.cargo_type || 'Unknown',
                    value: floatOrDefault(trip.truck?.cargo_value, 0),
                    route: `${trip.start_location_name} → ${trip.destination_name}`
                },
                risk: { score: Math.round(score), level: riskLevel, reasons: reasons.length ? [...new Set(reasons)] as string[] : ['Baseline transit'] },
                location: { lat, lng },
                status: trip.status
            });
        }

        return fleet.length > 0 ? fleet : SEED_FLEET;

    } catch (e) {
        console.warn('[RAKSHAK] Backend unreachable — using seed data.', e);
        return SEED_FLEET;
    }
}

export async function getAlerts(): Promise<Alert[]> {
    if (USE_MOCK) return SEED_ALERTS;

    try {
        const res = await fetch(`${API_BASE_URL}/alerts/`);
        if (!res.ok) throw new Error('alerts fetch failed');
        const data = await res.json();

        const mapped = data.map((d: any) => {
            const date = new Date(d.timestamp);
            return {
                id: d.alert_id,
                truckId: d.trip?.truck?.license_plate || 'TRK-???',
                time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                message: d.description,
                level: d.severity,
                aiExplanation: d.ai_explanation || '',
                riskScore: d.risk_score ?? undefined,
                type: d.alert_type || 'System',
            };
        }).sort((a: any, b: any) => (a.time > b.time ? -1 : 1));

        return mapped.length > 0 ? mapped : SEED_ALERTS;

    } catch (e) {
        console.warn('[RAKSHAK] Alerts API unreachable — using seed data.', e);
        return SEED_ALERTS;
    }
}

export async function triggerSimulation(tripId: string): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/simulate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trip_id: tripId })
        });
        return res.ok;
    } catch (e) {
        // Demo mode: simulate success
        console.warn('[RAKSHAK] Simulate endpoint unavailable — demo mode triggered.');
        return true;
    }
}

export async function getVisionDetection(): Promise<{ active: boolean; log: string[] }> {
    try {
        const res = await fetch(`${API_BASE_URL}/detect`);
        if (!res.ok) throw new Error('vision API failed');
        return await res.json();
    } catch {
        return {
            active: true,
            log: [
                'TR-1044: Person detected — confidence 0.97 — rear cargo door',
                'TR-102: Stopped vehicle — 2 individuals within 3m radius',
                'TR-557: Suspicious loitering — 58 seconds near cargo bay',
                'TR-721: Motion detected — cargo hold — low light conditions',
            ]
        };
    }
}

// Utility
function floatOrDefault(val: any, defaultVal: number): number {
    const parsed = parseFloat(val);
    return isNaN(parsed) ? defaultVal : parsed;
}

// ─── AUTH API ────────────────────────────────────────────────────────────────

export interface AuthUser {
    id: number;
    username: string;
    email: string;
    role: string;
}

export interface AuthTokens {
    access: string;
    refresh: string;
    user: AuthUser;
}

let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
    _accessToken = token;
    if (typeof window !== 'undefined') {
        if (token) localStorage.setItem('rakshak_token', token);
        else localStorage.removeItem('rakshak_token');
    }
}

export function getAccessToken(): string | null {
    if (_accessToken) return _accessToken;
    if (typeof window !== 'undefined') {
        return localStorage.getItem('rakshak_token');
    }
    return null;
}

function authHeaders(): HeadersInit {
    const token = getAccessToken();
    return token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };
}

export async function login(username: string, password: string): Promise<AuthTokens | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) throw new Error('Login failed');
        const data = await res.json();
        setAccessToken(data.access ?? null);
        return data as AuthTokens;
    } catch (e) {
        console.warn('[RAKSHAK] Login API unavailable.', e);
        return null;
    }
}

export async function logout(): Promise<void> {
    const token = getAccessToken();
    if (token) {
        try {
            await fetch(`${API_BASE_URL}/auth/logout/`, {
                method: 'POST',
                headers: authHeaders(),
            });
        } catch { /* ignore network errors on logout */ }
    }
    setAccessToken(null);
}

export async function getCurrentUser(): Promise<AuthUser | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/me/`, { headers: authHeaders() });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

// ─── RISK FUSION (live backend score) ────────────────────────────────────────

export interface RiskFusionResult {
    composite_score: number;         // 0–100
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    confidence: number;              // 0–1
    fusion_method: string;
    component_scores: {
        vision?: number;
        behaviour?: number;
        route?: number;
        digital_twin?: number;
    };
    triggered_rules: string[];
    explanation: string;
}

export async function getRiskFusion(tripId: string): Promise<RiskFusionResult | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/risk-fusion/?trip_id=${tripId}`, {
            headers: authHeaders(),
        });
        if (!res.ok) throw new Error('risk-fusion fetch failed');
        return await res.json();
    } catch (e) {
        console.warn('[RAKSHAK] Risk Fusion API unavailable.', e);
        return null;
    }
}

// ─── ROUTE AGENT ─────────────────────────────────────────────────────────────

export interface RouteCheckResult {
    in_safe_corridor: boolean;
    deviation_km: number;
    in_high_risk_zone: boolean;
    high_risk_zone_name: string | null;
    route_risk_score: number;         // 0–1
    alert_created: object | null;
}

export async function checkRoute(tripId: string, lat: number, lng: number): Promise<RouteCheckResult | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/route/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ trip_id: tripId, truck_id: tripId, gps_lat: lat, gps_lon: lng }),
        });
        if (!res.ok) throw new Error('route agent failed');
        return await res.json();
    } catch (e) {
        console.warn('[RAKSHAK] Route Agent unavailable.', e);
        return null;
    }
}

// ─── DIGITAL TWIN TELEMETRY ───────────────────────────────────────────────────

export interface TelemetryPayload {
    trip_id: string;
    truck_id: string;
    gps_lat: number;
    gps_lon: number;
    door_state: 'OPEN' | 'CLOSED';
    cargo_weight_kg: number;
    engine_on: boolean;
    driver_rfid_scanned: boolean;
    iot_signal_strength: number;  // 0.0–1.0
}

export interface DigitalTwinResult {
    twin_status: 'NORMAL' | 'DEGRADED' | 'CRITICAL';
    deviation_score: number;
    deviations: string[];
    alert_created: object | null;
}

export async function pushTelemetry(payload: TelemetryPayload): Promise<DigitalTwinResult | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/digital-twin/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('digital-twin failed');
        return await res.json();
    } catch (e) {
        console.warn('[RAKSHAK] Digital Twin API unavailable.', e);
        return null;
    }
}

// ─── BEHAVIOUR AGENT ─────────────────────────────────────────────────────────

export interface BehaviourTrack {
    track_id: number;
    dwell_seconds: number;
    velocity: { dx: number; dy: number };
    confidence: number;
}

export interface BehaviourResult {
    is_anomaly: boolean;
    anomaly_score: number;
    loitering_detected: boolean;
    loitering_duration_s: number;
    crowd_anomaly: boolean;
    flagged_track_ids: number[];
    alert_created: object | null;
}

export async function runBehaviourAnalysis(
    tripId: string,
    truckId: string,
    tracks: BehaviourTrack[]
): Promise<BehaviourResult | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/behaviour-analysis/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ trip_id: tripId, truck_id: truckId, tracks }),
        });
        if (!res.ok) throw new Error('behaviour agent failed');
        return await res.json();
    } catch (e) {
        console.warn('[RAKSHAK] Behaviour Agent unavailable.', e);
        return null;
    }
}

// ─── EXPLAINABILITY AGENT ────────────────────────────────────────────────────

export interface ExplainResult {
    explanation: string;
    recommended_action: string;
    confidence: number;
}

export async function explainAlert(alertId: string): Promise<ExplainResult | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/agents/explain/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ alert_id: alertId }),
        });
        if (!res.ok) throw new Error('explain endpoint failed');
        return await res.json();
    } catch (e) {
        console.warn('[RAKSHAK] Explain Agent unavailable.', e);
        return null;
    }
}

// ─── GPS LOG PUSH ─────────────────────────────────────────────────────────────
// Sends a real GPS ping to the backend for a given trip.

export async function pushGPSLog(tripId: string, lat: number, lng: number, speedKmh: number): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_URL}/gps-logs/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                trip: tripId,
                latitude: lat,
                longitude: lng,
                speed: speedKmh,
                timestamp: new Date().toISOString(),
            }),
        });
        return res.ok;
    } catch {
        return false;
    }
}

