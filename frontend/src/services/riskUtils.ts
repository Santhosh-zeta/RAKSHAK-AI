// RAKSHAK AI — Shared Route Constants & Risk Utility
// Used by both Journey Report and Risk Analysis pages
export const ROUTE_OPTIONS = [
    {
        label: 'Chennai → Mumbai', riskFactor: 0.65, distanceKm: 1340,
        dangerZones: ['NH48 Pune bypass', 'Nashik region'],
        path: [{ lat: 13.0827, lng: 80.2707 }, { lat: 15.3173, lng: 75.7139 }, { lat: 18.5204, lng: 73.8567 }, { lat: 19.0760, lng: 72.8777 }],
        dangerZoneMarks: [{ name: 'NH48 Pune bypass', lat: 18.5204, lng: 73.8567 }, { name: 'Nashik region', lat: 19.9975, lng: 73.7898 }]
    },
    {
        label: 'Delhi → Jaipur', riskFactor: 0.25, distanceKm: 270, dangerZones: [],
        path: [{ lat: 28.7041, lng: 77.1025 }, { lat: 26.9124, lng: 75.7873 }],
        dangerZoneMarks: []
    },
    {
        label: 'Surat → Ahmedabad', riskFactor: 0.45, distanceKm: 265, dangerZones: ['NH48 Surat stretch'],
        path: [{ lat: 21.1702, lng: 72.8311 }, { lat: 22.3039, lng: 73.1812 }, { lat: 23.0225, lng: 72.5714 }],
        dangerZoneMarks: [{ name: 'NH48 Surat stretch', lat: 21.5, lng: 72.9 }]
    },
    {
        label: 'Pune → Bangalore', riskFactor: 0.35, distanceKm: 840, dangerZones: [],
        path: [{ lat: 18.5204, lng: 73.8567 }, { lat: 15.8497, lng: 74.4977 }, { lat: 12.9716, lng: 77.5946 }],
        dangerZoneMarks: []
    },
    {
        label: 'Mumbai → Hyderabad', riskFactor: 0.55, distanceKm: 710, dangerZones: ['Solapur district'],
        path: [{ lat: 19.0760, lng: 72.8777 }, { lat: 17.6599, lng: 75.9064 }, { lat: 17.3850, lng: 78.4867 }],
        dangerZoneMarks: [{ name: 'Solapur district', lat: 17.6599, lng: 75.9064 }]
    },
    {
        label: 'Kolkata → Bhubaneswar', riskFactor: 0.70, distanceKm: 440, dangerZones: ['NH16 highway', 'Kharagpur stretch'],
        path: [{ lat: 22.5726, lng: 88.3639 }, { lat: 22.3302, lng: 87.3237 }, { lat: 20.2961, lng: 85.8245 }],
        dangerZoneMarks: [{ name: 'Kharagpur stretch', lat: 22.3302, lng: 87.3237 }]
    },
    {
        label: 'Delhi → Ludhiana', riskFactor: 0.45, distanceKm: 310, dangerZones: ['Ambala bypass'],
        path: [{ lat: 28.7041, lng: 77.1025 }, { lat: 30.3782, lng: 76.7767 }, { lat: 30.9010, lng: 75.8573 }],
        dangerZoneMarks: [{ name: 'Ambala bypass', lat: 30.3782, lng: 76.7767 }]
    },
    {
        label: 'Nagpur → Raipur', riskFactor: 0.30, distanceKm: 290, dangerZones: [],
        path: [{ lat: 21.1458, lng: 79.0882 }, { lat: 21.2514, lng: 81.6296 }],
        dangerZoneMarks: []
    },
    {
        label: 'Bangalore → Chennai', riskFactor: 0.25, distanceKm: 350, dangerZones: [],
        path: [{ lat: 12.9716, lng: 77.5946 }, { lat: 12.9202, lng: 79.1333 }, { lat: 13.0827, lng: 80.2707 }],
        dangerZoneMarks: []
    },
    {
        label: 'Mumbai → Ahmedabad', riskFactor: 0.50, distanceKm: 530, dangerZones: ['Vapi industrial zone'],
        path: [{ lat: 19.0760, lng: 72.8777 }, { lat: 20.3736, lng: 72.9068 }, { lat: 23.0225, lng: 72.5714 }],
        dangerZoneMarks: [{ name: 'Vapi industrial zone', lat: 20.3736, lng: 72.9068 }]
    },
];

export const CARGO_TYPE_OPTIONS = [
    { id: 'Electronics', riskFactor: 0.85, label: 'Electronics' },
    { id: 'Pharmaceuticals', riskFactor: 0.80, label: 'Pharma' },
    { id: 'Automotive', riskFactor: 0.60, label: 'Automotive' },
    { id: 'Textiles', riskFactor: 0.50, label: 'Textiles' },
    { id: 'Steel', riskFactor: 0.30, label: 'Steel' },
    { id: 'Cement', riskFactor: 0.20, label: 'Cement' },
];

export interface RiskBreakdownItem {
    label: string;
    score: number;
    weight: number;
}

export interface RiskReportResult {
    score: number;
    level: 'Low' | 'Medium' | 'High' | 'Critical';
    breakdown: RiskBreakdownItem[];
    reasons: string[];
    dangerZones: string[];
    routePath: { lat: number; lng: number }[];
    dangerZoneMarks: { lat: number; lng: number; name: string }[];
    timestamp: string;
}

export function computeRiskReport(params: {
    route: string;
    cargoType: string;
    travelTime: 'Day' | 'Night';
    cargoValue: number;
    distanceKm: number;
    driverExperienceYrs: number;
}): RiskReportResult {
    const routeData = ROUTE_OPTIONS.find(r => r.label === params.route) || ROUTE_OPTIONS[0];
    const cargoData = CARGO_TYPE_OPTIONS.find(c => c.id === params.cargoType) || CARGO_TYPE_OPTIONS[0];

    const routeRisk = Math.round(routeData.riskFactor * 100);
    const cargoRisk = Math.round(cargoData.riskFactor * 100);
    const timeRisk = params.travelTime === 'Night' ? 80 : 25;
    const valueRisk = params.cargoValue > 2000000 ? 90 : params.cargoValue > 1000000 ? 65 : params.cargoValue > 500000 ? 45 : 25;
    const driverRisk = Math.max(10, Math.round(100 - params.driverExperienceYrs * 8));

    const score = Math.round(
        routeRisk * 0.30 +
        cargoRisk * 0.25 +
        timeRisk * 0.20 +
        valueRisk * 0.15 +
        driverRisk * 0.10
    );

    const level: RiskReportResult['level'] =
        score >= 75 ? 'Critical' : score >= 55 ? 'High' : score >= 35 ? 'Medium' : 'Low';

    const reasons: string[] = [];
    if (params.travelTime === 'Night') reasons.push('Night transport significantly elevates theft risk');
    if (cargoRisk > 60) reasons.push(`${params.cargoType} is a high-value, easily-fenced cargo category`);
    if (routeRisk > 50) reasons.push(`${params.route} passes through known theft hotspots`);
    if (valueRisk > 60) reasons.push('High cargo value attracts organized theft operations');
    if (driverRisk > 50) reasons.push('Driver experience below recommended threshold for this route');
    if (routeData.dangerZones.length > 0) reasons.push(`Danger zones on route: ${routeData.dangerZones.join(', ')}`);
    if (score < 35) reasons.push('Standard precautions are sufficient for this journey');

    return {
        score,
        level,
        breakdown: [
            { label: 'Route Risk', score: routeRisk, weight: 30 },
            { label: 'Cargo Risk', score: cargoRisk, weight: 25 },
            { label: 'Time of Travel', score: timeRisk, weight: 20 },
            { label: 'Cargo Value', score: valueRisk, weight: 15 },
            { label: 'Driver Experience', score: driverRisk, weight: 10 },
        ],
        reasons,
        dangerZones: routeData.dangerZones,
        routePath: routeData.path || [],
        dangerZoneMarks: routeData.dangerZoneMarks || [],
        timestamp: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }),
    };
}
