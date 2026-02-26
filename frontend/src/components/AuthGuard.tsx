'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/context/AuthContext';

/**
 * AuthGuard — wraps page content behind authentication.
 * Redirects to /login if unauthenticated, shows a branded spinner while loading.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
        }
    }, [isLoading, isAuthenticated, router, pathname]);

    // Show branded loading screen while checking session
    if (isLoading) {
        return (
            <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', minHeight: '100vh', gap: '1.5rem',
                background: 'var(--bg, #0f172a)',
            }}>
                <div style={{ position: 'relative', width: 64, height: 64 }}>
                    <div style={{
                        position: 'absolute', inset: 0, borderRadius: '50%',
                        border: '3px solid rgba(59,130,246,0.15)',
                        borderTop: '3px solid #3b82f6',
                        animation: 'spin 1s linear infinite',
                    }} />
                    <div style={{
                        position: 'absolute', inset: 10, borderRadius: '50%',
                        border: '2px solid rgba(59,130,246,0.1)',
                        borderBottom: '2px solid #60a5fa',
                        animation: 'spin 1.5s linear infinite reverse',
                    }} />
                    <Image
                        src="/logo.png" alt="RAKSHAK AI" width={32} height={32}
                        style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
                    />
                </div>
                <span style={{ color: '#64748b', fontSize: '0.9rem', fontWeight: 600, letterSpacing: '0.05em' }}>
                    RAKSHAK AI — Authenticating...
                </span>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    // Not authenticated — redirect happening via useEffect, render nothing
    if (!isAuthenticated) return null;

    return <>{children}</>;
}
