import Link from 'next/link';
import Image from 'next/image';
import styles from './Navbar.module.css';

export default function Navbar() {
    return (
        <nav className={styles.navbar}>
            <Link href="/" className={styles.logoContainer}>
                <Image src="/logo.png" alt="Rakshak AI Logo" width={36} height={36} className={styles.navLogo} />
                <span className={styles.logoText}>
                    RAKSHAK AI
                </span>
            </Link>
            <div className={styles.navLinks}>
                <Link href="/" className={styles.navLink}>Home</Link>
                <Link href="/dashboard" className={styles.navLink}>Dashboard</Link>
                <Link href="/live-monitoring" className={styles.navLink}>Live Monitoring</Link>
                <Link href="/risk-analysis" className={styles.navLink}>Risk Analysis</Link>
                <Link href="/alerts" className={styles.navLink}>Alerts</Link>
            </div>
        </nav>
    );
}
