import { apiRequest } from "@/services/api/client";
import type { ATSScoreResponse, ResumeUploadResponse } from "@/services/api/types";

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<ResumeUploadResponse>("/resumes/upload", {
    method: "POST",
    body: formData,
  });
}

export async function getAtsScore(
  resumeId: string,
  jobDescription?: string
): Promise<ATSScoreResponse> {
  const trimmed = jobDescription?.trim();
  return apiRequest<ATSScoreResponse>(`/resumes/${resumeId}/ats-score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: trimmed ? trimmed : null }),
  });
}
