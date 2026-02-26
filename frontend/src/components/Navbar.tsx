'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import styles from './Navbar.module.css';
import { getAlerts } from '@/services/apiClient';
import { useAuth } from '@/context/AuthContext';
import { Menu, X, Bell, LogOut, User, ChevronDown } from 'lucide-react';

export default function Navbar() {
    const pathname = usePathname();
    const router = useRouter();
    const { isAuthenticated, user, logout } = useAuth();
    const [mobileOpen, setMobileOpen] = useState(false);
    const [criticalCount, setCriticalCount] = useState(0);
    const [userMenuOpen, setUserMenuOpen] = useState(false);

    // Fetch alert count badge — only when authenticated
    useEffect(() => {
        if (!isAuthenticated) { setCriticalCount(0); return; }
        async function fetchCount() {
            const alerts = await getAlerts();
            const high = alerts.filter(a => a.level === 'Critical' || a.level === 'High').length;
            setCriticalCount(high);
        }
        fetchCount();
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, [isAuthenticated]);

    const handleLogout = async () => {
        await logout();
        setUserMenuOpen(false);
        setMobileOpen(false);
        router.push('/login');
    };

    const navLinks = [
        { href: '/', label: 'Home' },
        { href: '/dashboard', label: 'Dashboard' },
        { href: '/fleet', label: 'Fleet' },
        { href: '/live-monitoring', label: 'Journey Report' },
        { href: '/risk-analysis', label: 'Risk Analysis' },
        { href: '/alerts', label: 'Alerts' },
    ];

    // Hide nav links on the login page
    const isLoginPage = pathname === '/login';

    const isActive = (href: string) =>
        href === '/' ? pathname === '/' : pathname.startsWith(href);

    const roleLabel = (role?: string) => {
        if (role === 'admin') return 'Platform Admin';
        if (role === 'company_user') return 'Fleet Manager';
        if (role === 'viewer') return 'Viewer';
        return role ?? '';
    };

    return (
        <nav className={styles.navbar}>
            {/* Logo */}
            <Link href="/" className={styles.logoContainer} aria-label="RAKSHAK AI Home">
                <Image src="/logo.png" alt="Rakshak AI Logo" width={36} height={36} className={styles.navLogo} />
                <span className={styles.logoText}>RAKSHAK AI</span>
            </Link>

            {/* Desktop Links — hidden on login page */}
            {!isLoginPage && (
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
            )}

            {/* Right side — auth controls */}
            <div className={styles.navRight}>
                {isAuthenticated && user ? (
                    /* ── User menu dropdown ─────────────────────────────────── */
                    <div className={styles.userMenuWrap}>
                        {criticalCount > 0 && (
                            <Link href="/alerts" className={styles.bellBtn} aria-label="Alerts">
                                <Bell size={18} />
                                <span className={styles.bellBadge}>{criticalCount}</span>
                            </Link>
                        )}
                        <button
                            className={styles.userBtn}
                            onClick={() => setUserMenuOpen(v => !v)}
                            aria-expanded={userMenuOpen}
                            aria-label="User menu"
                        >
                            <div className={styles.userAvatar}>
                                {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                            </div>
                            <div className={styles.userInfo}>
                                <span className={styles.userName}>{user.first_name || user.username}</span>
                                <span className={styles.userRole}>{roleLabel(user.role)}</span>
                            </div>
                            <ChevronDown size={14} className={`${styles.chevron} ${userMenuOpen ? styles.chevronOpen : ''}`} />
                        </button>

                        {userMenuOpen && (
                            <div className={styles.userDropdown}>
                                <div className={styles.dropdownHeader}>
                                    <p className={styles.dropdownName}>{user.username}</p>
                                    <p className={styles.dropdownRole}>{roleLabel(user.role)}</p>
                                </div>
                                <hr className={styles.dropdownDivider} />
                                <button className={styles.dropdownItem} onClick={handleLogout}>
                                    <LogOut size={14} /> Sign out
                                </button>
                            </div>
                        )}
                    </div>
                ) : (
                    /* ── Login button ─────────────────────────────────────── */
                    !isLoginPage && (
                        <Link href="/login" className={styles.loginBtn}>
                            <User size={15} /> Sign In
                        </Link>
                    )
                )}

                {/* Mobile hamburger — hidden on login page */}
                {!isLoginPage && (
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
                )}
            </div>

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
                    {isAuthenticated && (
                        <button className={styles.mobileLogout} onClick={handleLogout}>
                            <LogOut size={14} /> Sign out
                        </button>
                    )}
                    {!isAuthenticated && (
                        <Link href="/login" className={styles.mobileLink} onClick={() => setMobileOpen(false)}>
                            Sign In
                        </Link>
                    )}
                </div>
            )}
        </nav>
    );
}
