import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'Fleet Registry | RAKSHAK AI', description: 'View all trucks, drivers, and active trips from the live database.' };
export default function FleetLayout({ children }: { children: React.ReactNode }) { return <>{children}</>; }
