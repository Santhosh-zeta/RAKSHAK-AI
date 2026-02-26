'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import styles from './Navbar.module.css';
import { getAlerts } from '@/services/apiClient';
import { Menu, X, Bell } from 'lucide-react';

export default function Navbar() {
    const pathname = usePathname();
    const [mobileOpen, setMobileOpen] = useState(false);
    const [criticalCount, setCriticalCount] = useState(0);

    // Fetch alert count badge (N3)
    useEffect(() => {
        async function fetchCount() {
            const alerts = await getAlerts();
            const high = alerts.filter(a => a.level === 'Critical' || a.level === 'High').length;
            setCriticalCount(high);
        }
        fetchCount();
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, []);

    const navLinks = [
        { href: '/', label: 'Home' },
        { href: '/dashboard', label: 'Dashboard' },
        { href: '/live-monitoring', label: 'Journey Report' },
        { href: '/risk-analysis', label: 'Risk Analysis' },
        { href: '/alerts', label: 'Alerts' },
    ];

    const isActive = (href: string) =>
        href === '/' ? pathname === '/' : pathname.startsWith(href);

    return (
        <nav className={styles.navbar}>
            {/* Logo */}
            <Link href="/" className={styles.logoContainer} aria-label="RAKSHAK AI Home">
                <Image src="/logo.png" alt="Rakshak AI Logo" width={36} height={36} className={styles.navLogo} />
                <span className={styles.logoText}>RAKSHAK AI</span>
            </Link>

            {/* Desktop Links */}
            <div className={styles.navLinks}>
                {navLinks.map(({ href, label }) => (
                    <Link
                        key={href}
                        href={href}
                        className={`${styles.navLink} ${isActive(href) ? styles.activeLink : ''}`}
                        aria-current={isActive(href) ? 'page' : undefined}
                    >
                        {label}
                        {href === '/alerts' && criticalCount > 0 && (
                            <span className={styles.alertBadge} aria-label={`${criticalCount} high-priority alerts`}>
                                {criticalCount}
                            </span>
                        )}
                        {isActive(href) && <span className={styles.activeDot} />}
                    </Link>
                ))}
            </div>

            {/* Mobile Hamburger Button */}
            <button
                className={styles.hamburger}
                onClick={() => setMobileOpen(v => !v)}
                aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={mobileOpen}
            >
                {mobileOpen ? <X size={22} /> : <Menu size={22} />}
                {criticalCount > 0 && !mobileOpen && (
                    <span className={styles.hamburgerBadge}>{criticalCount}</span>
                )}
            </button>

            {/* Mobile Dropdown */}
            {mobileOpen && (
                <div className={styles.mobileMenu}>
                    {navLinks.map(({ href, label }) => (
                        <Link
                            key={href}
                            href={href}
                            className={`${styles.mobileLink} ${isActive(href) ? styles.mobileLinkActive : ''}`}
                            onClick={() => setMobileOpen(false)}
                            aria-current={isActive(href) ? 'page' : undefined}
                        >
                            {label}
                            {href === '/alerts' && criticalCount > 0 && (
                                <span className={styles.alertBadge}>{criticalCount}</span>
                            )}
                        </Link>
                    ))}
                </div>
            )}
        </nav>
    );
}
