import { apiRequest } from "@/services/api/client";
import type {
  FinalAssessment,
  InterviewAnswerResponse,
  InterviewQuestionResponse,
  InterviewStartRequest,
  InterviewStateResponse,
  QuestionDifficulty,
} from "@/services/api/types";

export async function startInterview(
  resumeId: string,
  objective: string,
  difficulty: QuestionDifficulty
): Promise<InterviewQuestionResponse> {
  const payload: InterviewStartRequest = { resume_id: resumeId, objective, difficulty };
  return apiRequest<InterviewQuestionResponse>("/interviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function submitAnswer(
  interviewId: string,
  turnId: string,
  answer: string
): Promise<InterviewAnswerResponse> {
  return apiRequest<InterviewAnswerResponse>(`/interviews/${interviewId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ turn_id: turnId, answer }),
  });
}

export async function getInterview(interviewId: string): Promise<InterviewStateResponse> {
  return apiRequest<InterviewStateResponse>(`/interviews/${interviewId}`);
}

export async function completeInterview(interviewId: string): Promise<InterviewStateResponse> {
  return apiRequest<InterviewStateResponse>(`/interviews/${interviewId}/complete`, {
    method: "POST",
  });
}

export async function createAssessment(interviewId: string): Promise<FinalAssessment> {
  return apiRequest<FinalAssessment>(`/interviews/${interviewId}/assessment`, { method: "POST" });
}

export async function getAssessment(interviewId: string): Promise<FinalAssessment> {
  return apiRequest<FinalAssessment>(`/interviews/${interviewId}/assessment`);
}
