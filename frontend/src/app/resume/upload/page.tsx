"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import RequireAuth from "@/components/RequireAuth";
import { uploadResume } from "@/services/resume";
import type { ResumeUploadResponse } from "@/services/api/types";

type UploadStatus = "idle" | "uploading" | "done" | "error";

function ResumeUpload() {
  const router = useRouter();
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeUploadResponse | null>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setStatus("uploading");
    setErrorMessage(null);
    setResult(null);

    try {
      const response = await uploadResume(file);
      setResult(response);
      setStatus("done");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
      setStatus("error");
    }
  };

  const handleStartInterview = () => {
    if (!result) {
      return;
    }
    const params = new URLSearchParams({
      resumeId: result.resume_id,
      candidateId: result.candidate_id,
    });
    router.push(`/interview/setup?${params.toString()}`);
  };

  const handleAnalyzeResume = () => {
    if (!result) {
      return;
    }
    router.push(`/resume/analysis?resumeId=${result.resume_id}`);
  };

  const profile = result?.profile;

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Upload your resume</h1>
        <p>Upload a PDF resume to build your candidate profile and start an interview.</p>
      </div>

      <label className="label" htmlFor="resume-file">
        Resume (PDF)
      </label>
      <input
        id="resume-file"
        className="field"
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        disabled={status === "uploading"}
      />

      {status === "uploading" && (
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Uploading and processing your resume…
        </p>
      )}

      {status === "error" && errorMessage && <div className="error-banner">{errorMessage}</div>}

      {status === "done" && profile && (
        <div className="card">
          <h2>{profile.identity.full_name ?? "Candidate profile"}</h2>
          {profile.identity.email && <p>{profile.identity.email}</p>}
          {profile.professional_summary && <p>{profile.professional_summary}</p>}

          {profile.skills.length > 0 && (
            <div className="badge-row">
              {profile.skills.slice(0, 8).map((skill) => (
                <span key={skill.name} className="badge">
                  {skill.name}
                </span>
              ))}
            </div>
          )}

          <p className="progress-label">
            {profile.experience.length} experience entr{profile.experience.length === 1 ? "y" : "ies"} ·{" "}
            {profile.claims.length} claim{profile.claims.length === 1 ? "" : "s"} identified
          </p>

          <div className="actions">
            <button type="button" className="button" onClick={handleStartInterview}>
              Start Interview
            </button>
            <button type="button" className="button secondary" onClick={handleAnalyzeResume}>
              Analyze resume
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

export default function ResumeUploadPage() {
  return (
    <RequireAuth>
      <ResumeUpload />
    </RequireAuth>
  );
}
