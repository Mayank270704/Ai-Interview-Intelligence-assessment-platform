"use client";

import Link from "next/link";

import RequireAuth from "@/components/RequireAuth";
import { useAuth } from "@/context/AuthContext";

function Dashboard() {
  const { user } = useAuth();

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Your dashboard</h1>
        <p>
          Signed in as <strong>{user?.email ?? "your account"}</strong>.
        </p>
      </div>

      <div className="card">
        <h2>Practice an interview</h2>
        <p>
          Upload a resume to build your candidate profile, then run a text, voice, or video
          interview grounded in your real experience.
        </p>
        <div className="actions">
          <Link href="/resume/upload" className="button">
            Upload a resume
          </Link>
        </div>
      </div>

      <div className="card">
        <h2>Score your resume</h2>
        <p>
          Check how your resume reads to an applicant tracking system, on its own or against a
          specific job description. Upload a resume first, then open its analysis.
        </p>
        <div className="actions">
          <Link href="/resume/upload" className="button secondary">
            Start with a resume
          </Link>
        </div>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}
