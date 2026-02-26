import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import Navbar from "@/components/Navbar";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RAKSHAK AI | Predictive Cargo Theft Intelligence",
  description: "AI system that predicts cargo theft before it happens.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={plusJakartaSans.className} suppressHydrationWarning>
        <Navbar />
        <main className="main-content">
          {children}
        </main>
      </body>
    </html>
  );
}


