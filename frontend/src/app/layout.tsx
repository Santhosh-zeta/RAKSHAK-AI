import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Navbar from "@/components/Navbar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800", "900"] });

export const metadata: Metadata = {
  title: {
    default: "RAKSHAK AI | Predictive Cargo Theft Intelligence",
    template: "%s | RAKSHAK AI",
  },
  description: "AI-powered predictive cargo theft prevention system — Computer Vision, Behavioral Analytics, Route Intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <Navbar />
        <main className="main-content">
          {children}
        </main>
      </body>
    </html>
  );
}


