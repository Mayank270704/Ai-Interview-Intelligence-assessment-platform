"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { uploadResume } from "@/services/resume";
import type { ResumeUploadResponse } from "@/services/api/types";

type UploadStatus = "idle" | "uploading" | "done" | "error";

export default function ResumeUploadPage() {
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

  const profile = result?.profile;

  return (
    <main className="narrow">
      <h1>Upload your resume</h1>
      <p>Upload a PDF resume to build your candidate profile and start an interview.</p>

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

      {status === "uploading" && <p className="progress-label">Uploading and processing your resume…</p>}

      {status === "error" && errorMessage && <div className="error-banner">{errorMessage}</div>}

      {status === "done" && profile && (
        <div className="card">
          <h2>{profile.identity.full_name ?? "Candidate profile"}</h2>
          {profile.identity.email && <p>{profile.identity.email}</p>}
          {profile.professional_summary && <p>{profile.professional_summary}</p>}

          {profile.skills.length > 0 && (
            <p>
              {profile.skills.slice(0, 8).map((skill) => (
                <span key={skill.name} className="badge">
                  {skill.name}
                </span>
              ))}
            </p>
          )}

          <p className="progress-label">
            {profile.experience.length} experience entr{profile.experience.length === 1 ? "y" : "ies"} ·{" "}
            {profile.claims.length} claim{profile.claims.length === 1 ? "" : "s"} identified
          </p>

          <button type="button" className="button" onClick={handleStartInterview}>
            Start Interview
          </button>
        </div>
      )}
    </main>
  );
}
