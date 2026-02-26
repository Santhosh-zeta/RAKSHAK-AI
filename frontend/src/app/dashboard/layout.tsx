import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Dashboard',
    description: 'Live fleet monitoring and AI threat intelligence command center.',
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
