'use client';

import Link from 'next/link';

export default function SDGFloatingBtn() {
    return (
        <Link
            href="/sustainability"
            id="sdg-floating-btn"
            aria-label="View UN Sustainable Development Goals alignment"
            style={{
                position: 'fixed',
                bottom: '1.75rem',
                right: '1.75rem',
                zIndex: 9999,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'linear-gradient(135deg, #3F7E44, #10b981)',
                color: 'white',
                padding: '0.65rem 1.2rem',
                borderRadius: '999px',
                fontWeight: 800,
                fontSize: '0.82rem',
                textDecoration: 'none',
                boxShadow: '0 4px 20px rgba(63, 126, 68, 0.45), 0 2px 8px rgba(0,0,0,0.12)',
                letterSpacing: '0.4px',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                border: '2px solid rgba(255,255,255,0.22)',
                backdropFilter: 'blur(8px)',
                whiteSpace: 'nowrap',
            }}
            onMouseEnter={e => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.transform = 'translateY(-3px) scale(1.05)';
                el.style.boxShadow = '0 10px 30px rgba(63, 126, 68, 0.55), 0 4px 12px rgba(0,0,0,0.15)';
            }}
            onMouseLeave={e => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.transform = '';
                el.style.boxShadow = '0 4px 20px rgba(63, 126, 68, 0.45), 0 2px 8px rgba(0,0,0,0.12)';
            }}
        >
            <span style={{ fontSize: '1rem', lineHeight: 1 }}>🌿</span>
            <span>SDG 9 · 12 · 13</span>
        </Link>
    );
}
