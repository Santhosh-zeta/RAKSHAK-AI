// app/login/layout.tsx — wraps the login page in Suspense
// Required because page.tsx uses useSearchParams() which needs a Suspense boundary
// in the Next.js App Router.
import { Suspense } from 'react';

export default function LoginLayout({ children }: { children: React.ReactNode }) {
    return <Suspense fallback={<div style={{ minHeight: '100vh', background: '#060b14' }} />}>{children}</Suspense>;
}
