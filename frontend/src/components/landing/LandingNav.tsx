"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const SECTIONS = [
  { href: "#platform", label: "Platform" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#intelligence", label: "Intelligence" },
  { href: "#assessment", label: "Assessment" },
];

export default function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  return (
    <nav className="lp-nav" data-scrolled={scrolled} aria-label="Main">
      <div className="lp-shell lp-nav-inner">
        <Link href="/" className="lp-brand">
          <span className="lp-brand-mark" aria-hidden="true" />
          Interview Intelligence
        </Link>

        <div className="lp-nav-links">
          {SECTIONS.map((section) => (
            <a key={section.href} href={section.href}>
              {section.label}
            </a>
          ))}
        </div>

        <div className="lp-nav-actions">
          <Link href="/login" className="lp-nav-login">
            Login
          </Link>
          <Link href="/resume/upload" className="lp-btn lp-btn--primary">
            Start Interview
            <span className="lp-btn-arrow" aria-hidden="true">
              →
            </span>
          </Link>
        </div>

        <button
          type="button"
          className="lp-burger"
          aria-expanded={menuOpen}
          aria-controls="lp-mobile-menu"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>

      <div className="lp-mobile-menu" id="lp-mobile-menu" data-open={menuOpen} hidden={!menuOpen}>
        {SECTIONS.map((section) => (
          <a key={section.href} href={section.href} onClick={() => setMenuOpen(false)}>
            {section.label}
          </a>
        ))}
        <a href="/login" onClick={() => setMenuOpen(false)}>
          Login
        </a>
        <Link
          href="/resume/upload"
          className="lp-btn lp-btn--primary"
          onClick={() => setMenuOpen(false)}
        >
          Start Interview
          <span className="lp-btn-arrow" aria-hidden="true">
            →
          </span>
        </Link>
      </div>
    </nav>
  );
}
