"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import HeaderNav from "@/components/HeaderNav";

/**
 * The application header.
 *
 * The marketing landing page ships its own navigation, so this steps aside
 * there rather than stacking a second header above it. Every application route
 * keeps the header exactly as before.
 */
export default function SiteHeader() {
  const pathname = usePathname();

  if (pathname === "/") {
    return null;
  }

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link href="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          AI Interview Intelligence
        </Link>
        <HeaderNav />
      </div>
    </header>
  );
}
