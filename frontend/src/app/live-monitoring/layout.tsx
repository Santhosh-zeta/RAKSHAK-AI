import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Journey Report',
    description: 'AI-powered pre-journey risk assessment for cargo transport.',
};

export default function JourneyLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
