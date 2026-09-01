import { apiRequest } from "@/services/api/client";
import type { ResumeUploadResponse } from "@/services/api/types";

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<ResumeUploadResponse>("/resumes/upload", {
    method: "POST",
    body: formData,
  });
}
