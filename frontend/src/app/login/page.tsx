'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth, RegisterCompanyPayload } from '@/context/AuthContext';
import styles from './page.module.css';
import { Eye, EyeOff, Shield, Building2, User, Lock, Mail, MapPin, ArrowRight, Loader2 } from 'lucide-react';

type Mode = 'login' | 'register';

export default function AuthPage() {
    const { login, registerCompany, isAuthenticated } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [mode, setMode] = useState<Mode>('login');
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    // Login fields
    const [loginForm, setLoginForm] = useState({ username: '', password: '' });

    // Register fields
    const [regForm, setRegForm] = useState<RegisterCompanyPayload>({
        company_name: '', company_city: '', username: '',
        password: '', email: '', first_name: '', last_name: '',
    });

    // Redirect if already logged in
    useEffect(() => {
        if (isAuthenticated) {
            const redirect = searchParams.get('redirect') || '/dashboard';
            router.replace(redirect);
        }
    }, [isAuthenticated, router, searchParams]);

    // ── Login submit ─────────────────────────────────────────────────────────────
    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!loginForm.username || !loginForm.password) {
            setError('Username and password are required.');
            return;
        }
        setBusy(true);
        const result = await login(loginForm.username, loginForm.password);
        setBusy(false);
        if (!result.ok) setError(result.error || 'Login failed.');
        // redirect handled by useEffect above
    };

    // ── Register submit ──────────────────────────────────────────────────────────
    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        const { company_name, username, password, email } = regForm;
        if (!company_name || !username || !password || !email) {
            setError('Company name, username, email and password are required.');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }
        setBusy(true);
        const result = await registerCompany(regForm);
        setBusy(false);
        if (!result.ok) setError(result.error || 'Registration failed.');
    };

    return (
        <div className={styles.page}>
            {/* Left panel — branding */}
            <div className={styles.brandPanel}>
                <div className={styles.brandInner}>
                    <div className={styles.brandLogo}>
                        <Image src="/logo.png" alt="Rakshak AI" width={48} height={48} />
                        <span>RAKSHAK AI</span>
                    </div>
                    <h1 className={styles.brandHeadline}>
                        Predictive Cargo<br />Security Intelligence
                    </h1>
                    <p className={styles.brandSub}>
                        AI-powered multi-agent platform that fuses computer vision,
                        geospatial analytics, and behavioural AI to prevent cargo theft
                        before it happens.
                    </p>
                    <div className={styles.brandStats}>
                        <div className={styles.brandStat}><strong>99.2%</strong><span>Detection Rate</span></div>
                        <div className={styles.brandStat}><strong>&lt;50ms</strong><span>Vision Latency</span></div>
                        <div className={styles.brandStat}><strong>₹2.5B+</strong><span>Cargo Secured</span></div>
                    </div>
                    <div className={styles.brandAgents}>
                        {['YOLO Vision', 'DeepSort Tracker', 'IsolationForest', 'Shapely Geofence', 'Risk Fusion', 'LLM Explainer'].map(a => (
                            <span key={a} className={styles.agentChip}>{a}</span>
                        ))}
                    </div>
                </div>
                {/* Background grid glow */}
                <div className={styles.brandGlow} />
            </div>

            {/* Right panel — form */}
            <div className={styles.formPanel}>
                <div className={styles.formCard}>
                    {/* Mode switcher tabs */}
                    <div className={styles.modeTabs}>
                        <button
                            className={`${styles.modeTab} ${mode === 'login' ? styles.modeTabActive : ''}`}
                            onClick={() => { setMode('login'); setError(''); }}
                        >
                            <User size={15} /> Sign In
                        </button>
                        <button
                            className={`${styles.modeTab} ${mode === 'register' ? styles.modeTabActive : ''}`}
                            onClick={() => { setMode('register'); setError(''); }}
                        >
                            <Building2 size={15} /> Register Company
                        </button>
                    </div>

                    {/* ── LOGIN FORM ─────────────────────────────────────────────────── */}
                    {mode === 'login' && (
                        <form onSubmit={handleLogin} className={styles.form} autoComplete="on">
                            <div className={styles.formHeader}>
                                <Shield size={28} className={styles.formIcon} />
                                <h2>Welcome back</h2>
                                <p>Sign in to your RAKSHAK command centre</p>
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="login-username">Username</label>
                                <div className={styles.inputWrap}>
                                    <User size={16} className={styles.inputIcon} />
                                    <input
                                        id="login-username"
                                        type="text"
                                        placeholder="admin"
                                        autoComplete="username"
                                        value={loginForm.username}
                                        onChange={e => setLoginForm(f => ({ ...f, username: e.target.value }))}
                                    />
                                </div>
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="login-password">Password</label>
                                <div className={styles.inputWrap}>
                                    <Lock size={16} className={styles.inputIcon} />
                                    <input
                                        id="login-password"
                                        type={showPw ? 'text' : 'password'}
                                        placeholder="••••••••"
                                        autoComplete="current-password"
                                        value={loginForm.password}
                                        onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))}
                                    />
                                    <button type="button" className={styles.eyeBtn} onClick={() => setShowPw(v => !v)} tabIndex={-1}>
                                        {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>
                            </div>

                            {error && <div className={styles.errorBox}>{error}</div>}

                            <button type="submit" className={styles.submitBtn} disabled={busy} id="login-submit-btn">
                                {busy ? <Loader2 size={18} className={styles.spinner} /> : <ArrowRight size={18} />}
                                {busy ? 'Signing in…' : 'Sign In'}
                            </button>

                            <p className={styles.switchHint}>
                                New company?{' '}
                                <button type="button" className={styles.switchLink} onClick={() => { setMode('register'); setError(''); }}>
                                    Register here →
                                </button>
                            </p>
                        </form>
                    )}

                    {/* ── REGISTER FORM ──────────────────────────────────────────────── */}
                    {mode === 'register' && (
                        <form onSubmit={handleRegister} className={styles.form} autoComplete="on">
                            <div className={styles.formHeader}>
                                <Building2 size={28} className={styles.formIcon} />
                                <h2>Register your company</h2>
                                <p>Get started with RAKSHAK AI — free setup</p>
                            </div>

                            <div className={styles.fieldRow}>
                                <div className={styles.field}>
                                    <label htmlFor="reg-company-name">Company Name <span className={styles.req}>*</span></label>
                                    <div className={styles.inputWrap}>
                                        <Building2 size={16} className={styles.inputIcon} />
                                        <input id="reg-company-name" type="text" placeholder="NextGen Logistics"
                                            value={regForm.company_name}
                                            onChange={e => setRegForm(f => ({ ...f, company_name: e.target.value }))} />
                                    </div>
                                </div>
                                <div className={styles.field}>
                                    <label htmlFor="reg-company-city">City</label>
                                    <div className={styles.inputWrap}>
                                        <MapPin size={16} className={styles.inputIcon} />
                                        <input id="reg-company-city" type="text" placeholder="Delhi"
                                            value={regForm.company_city}
                                            onChange={e => setRegForm(f => ({ ...f, company_city: e.target.value }))} />
                                    </div>
                                </div>
                            </div>

                            <div className={styles.fieldRow}>
                                <div className={styles.field}>
                                    <label htmlFor="reg-first">First Name</label>
                                    <div className={styles.inputWrap}>
                                        <User size={16} className={styles.inputIcon} />
                                        <input id="reg-first" type="text" placeholder="Raj"
                                            value={regForm.first_name}
                                            onChange={e => setRegForm(f => ({ ...f, first_name: e.target.value }))} />
                                    </div>
                                </div>
                                <div className={styles.field}>
                                    <label htmlFor="reg-last">Last Name</label>
                                    <div className={styles.inputWrap}>
                                        <User size={16} className={styles.inputIcon} />
                                        <input id="reg-last" type="text" placeholder="Kumar"
                                            value={regForm.last_name}
                                            onChange={e => setRegForm(f => ({ ...f, last_name: e.target.value }))} />
                                    </div>
                                </div>
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="reg-email">Email <span className={styles.req}>*</span></label>
                                <div className={styles.inputWrap}>
                                    <Mail size={16} className={styles.inputIcon} />
                                    <input id="reg-email" type="email" placeholder="ops@company.com"
                                        autoComplete="email"
                                        value={regForm.email}
                                        onChange={e => setRegForm(f => ({ ...f, email: e.target.value }))} />
                                </div>
                            </div>

                            <div className={styles.fieldRow}>
                                <div className={styles.field}>
                                    <label htmlFor="reg-username">Username <span className={styles.req}>*</span></label>
                                    <div className={styles.inputWrap}>
                                        <User size={16} className={styles.inputIcon} />
                                        <input id="reg-username" type="text" placeholder="nextgen_admin"
                                            autoComplete="username"
                                            value={regForm.username}
                                            onChange={e => setRegForm(f => ({ ...f, username: e.target.value }))} />
                                    </div>
                                </div>
                                <div className={styles.field}>
                                    <label htmlFor="reg-password">Password <span className={styles.req}>*</span></label>
                                    <div className={styles.inputWrap}>
                                        <Lock size={16} className={styles.inputIcon} />
                                        <input id="reg-password" type={showPw ? 'text' : 'password'} placeholder="Min 8 chars"
                                            autoComplete="new-password"
                                            value={regForm.password}
                                            onChange={e => setRegForm(f => ({ ...f, password: e.target.value }))} />
                                        <button type="button" className={styles.eyeBtn} onClick={() => setShowPw(v => !v)} tabIndex={-1}>
                                            {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {error && <div className={styles.errorBox}>{error}</div>}

                            <button type="submit" className={styles.submitBtn} disabled={busy} id="register-submit-btn">
                                {busy ? <Loader2 size={18} className={styles.spinner} /> : <Building2 size={18} />}
                                {busy ? 'Creating account…' : 'Create Company Account'}
                            </button>

                            <p className={styles.switchHint}>
                                Already registered?{' '}
                                <button type="button" className={styles.switchLink} onClick={() => { setMode('login'); setError(''); }}>
                                    Sign in →
                                </button>
                            </p>
                        </form>
                    )}

                    <div className={styles.formFooter}>
                        <Link href="/" className={styles.backHome}>← Back to homepage</Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
