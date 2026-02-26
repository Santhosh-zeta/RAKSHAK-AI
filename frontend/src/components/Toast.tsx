'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, X } from 'lucide-react';

interface ToastProps {
    message: string;
    type?: 'success' | 'error' | 'warning';
    onClose: () => void;
    duration?: number;
}

export function Toast({ message, type = 'success', onClose, duration = 4000 }: ToastProps) {
    useEffect(() => {
        const t = setTimeout(onClose, duration);
        return () => clearTimeout(t);
    }, [onClose, duration]);

    const colors = {
        success: { bg: '#059669', border: '#047857' },
        error: { bg: '#ef4444', border: '#dc2626' },
        warning: { bg: '#f59e0b', border: '#d97706' },
    }[type];

    return (
        <div
            role="alert"
            aria-live="polite"
            style={{
                position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
                background: colors.bg, color: 'white',
                padding: '14px 20px', borderRadius: 12,
                display: 'flex', alignItems: 'center', gap: 10,
                boxShadow: `0 8px 24px ${colors.bg}50`,
                border: `1px solid ${colors.border}`,
                animation: 'slideInToast 0.3s cubic-bezier(0.34,1.56,0.64,1)',
                fontWeight: 700, fontSize: '0.95rem',
                minWidth: 240, maxWidth: 380,
            }}
        >
            {type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span style={{ flex: 1 }}>{message}</span>
            <button
                onClick={onClose}
                aria-label="Dismiss notification"
                style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', padding: 2, opacity: 0.8 }}
            >
                <X size={16} />
            </button>
            <style>{`
                @keyframes slideInToast {
                    from { opacity: 0; transform: translateX(100px) scale(0.9); }
                    to   { opacity: 1; transform: translateX(0) scale(1); }
                }
            `}</style>
        </div>
    );
}

// Hook for easy toast usage
export function useToast() {
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' } | null>(null);

    const showToast = (message: string, type: 'success' | 'error' | 'warning' = 'success') => {
        setToast({ message, type });
    };

    const ToastElement = toast ? (
        <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
        />
    ) : null;

    return { showToast, ToastElement };
}
