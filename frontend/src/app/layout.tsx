import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";

import HeaderNav from "@/components/HeaderNav";
import { AuthProvider } from "@/context/AuthContext";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AI Interview Intelligence",
  description: "Interview preparation and assessment platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>
          <header className="site-header">
            <div className="site-header-inner">
              <Link href="/" className="brand">
                <span className="brand-mark" aria-hidden="true" />
                AI Interview Intelligence
              </Link>
              <HeaderNav />
            </div>
          </header>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
