"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/context/AuthContext";

export default function HeaderNav() {
  const { status, user, logOut } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  if (status === "loading") {
    return <nav className="header-nav" aria-hidden="true" />;
  }

  if (status === "anonymous") {
    return (
      <nav className="header-nav">
        <Link href="/login" className="button secondary">
          Log in
        </Link>
        <Link href="/signup" className="button">
          Sign up
        </Link>
      </nav>
    );
  }

  const handleLogOut = async () => {
    setSigningOut(true);
    await logOut();
    setSigningOut(false);
    router.push("/");
  };

  return (
    <nav className="header-nav">
      <Link href="/dashboard" className="header-user">
        {user?.email ?? "My account"}
      </Link>
      <button type="button" className="button secondary" onClick={handleLogOut} disabled={signingOut}>
        {signingOut ? "Signing out…" : "Log out"}
      </button>
    </nav>
  );
}
