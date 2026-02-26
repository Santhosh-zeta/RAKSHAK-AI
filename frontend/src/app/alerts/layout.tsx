import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Alerts',
    description: 'Real-time threat alerts with AI explainability for cargo theft prevention.',
};

export default function AlertsLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
