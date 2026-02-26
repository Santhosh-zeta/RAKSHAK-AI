import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Risk Analysis',
    description: 'Machine learning risk factor analysis and trip risk prediction engine.',
};

export default function RiskLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
