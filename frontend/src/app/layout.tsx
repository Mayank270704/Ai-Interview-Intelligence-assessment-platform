import type { Metadata } from "next";
import { Inter } from "next/font/google";

import SiteHeader from "@/components/SiteHeader";
import { AuthProvider } from "@/context/AuthContext";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "AI Interview Intelligence",
    template: "%s · AI Interview Intelligence",
  },
  description:
    "Adaptive AI interviews that analyze your answers, verify resume claims, track your knowledge state, and decide what to ask next.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>
          <SiteHeader />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
