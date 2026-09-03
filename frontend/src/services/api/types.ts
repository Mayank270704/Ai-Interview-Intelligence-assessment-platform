export type QuestionDifficulty = "easy" | "medium" | "hard";

export interface CandidateIdentity {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
}

export interface Skill {
  name: string;
  proficiency: string | null;
}

export interface Technology {
  name: string;
  category: string | null;
}

export interface Experience {
  company: string;
  position: string;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface Project {
  name: string;
  description: string | null;
  technologies: string[] | null;
}

export interface Education {
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  end_date: string | null;
}

export interface Claim {
  claim_id: string | null;
  claim_text: string;
  category: string;
  context: string | null;
  resume_evidence: string;
}

export interface CandidateProfile {
  identity: CandidateIdentity;
  professional_summary: string | null;
  education: Education[];
  skills: Skill[];
  technologies: Technology[];
  experience: Experience[];
  projects: Project[];
  claims: Claim[];
  languages: string[];
}

export interface ResumeUploadResponse {
  resume_id: string;
  candidate_id: string;
  profile: CandidateProfile;
}

export interface GeneratedQuestion {
  question: string;
  target_concept: string;
  difficulty: QuestionDifficulty;
  intent: string;
  evaluation_focus: string[];
}

export interface InterviewStartRequest {
  objective: string;
  difficulty: QuestionDifficulty;
  resume_id: string;
}

export interface InterviewQuestionResponse {
  interview_id: string;
  candidate_id: string;
  resume_id: string | null;
  difficulty: QuestionDifficulty;
  turn_id: string;
  question: GeneratedQuestion;
}

export interface AnsweredTurn {
  turn_id: string;
  turn_number: number;
  question: GeneratedQuestion;
  answer: string;
}

export interface InterviewAnswerResponse {
  interview_id: string;
  answered_turn: AnsweredTurn;
  next_turn_id: string;
  next_question: GeneratedQuestion;
  difficulty: QuestionDifficulty;
  knowledge_state: CandidateKnowledgeState;
}

export interface InterviewTurn {
  id: string;
  turn_number: number;
  question: GeneratedQuestion;
  answer: string | null;
  created_at: string;
}

export type ConceptConfidence = "low" | "medium" | "high";
export type ClaimVerificationStatus = "supported" | "unsupported" | "uncertain";

export interface ConceptState {
  concept: string;
  confidence: ConceptConfidence;
  demonstrated: boolean;
  missing: boolean;
  incorrect: boolean;
}

export interface ClaimVerification {
  claim_id: string | null;
  claim_text: string;
  status: ClaimVerificationStatus;
  confidence: ConceptConfidence;
}

export interface CandidateKnowledgeState {
  concept_states: ConceptState[];
  claim_verifications: ClaimVerification[];
  summary: string;
}

export type InterviewStatus = "created" | "in_progress" | "completed";

export interface InterviewStateResponse {
  interview_id: string;
  candidate_id: string;
  resume_id: string | null;
  objective: string;
  difficulty: QuestionDifficulty;
  status: InterviewStatus;
  current_question: GeneratedQuestion | null;
  knowledge_state: CandidateKnowledgeState;
  turns: InterviewTurn[];
}

/* Authentication */

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  user_id: string;
  email: string | null;
}

export interface SignUpResponse {
  user_id: string;
  email: string | null;
  email_confirmation_required: boolean;
  session: AuthSession | null;
}

export interface CurrentUser {
  id: string;
  email: string | null;
}

/* ATS resume score */

export type ATSMode = "readiness" | "jd_match";

export interface ATSDiagnostic {
  type: string;
  section: string;
  affected_text: string | null;
  explanation: string;
  actionable_fix: string;
}

export interface ATSScoreResponse {
  resume_id: string;
  ats_score: number;
  mode: ATSMode;
  matched_keywords: string[];
  missing_keywords: string[];
  matched_skills: string[];
  missing_skills: string[];
  section_feedback: string[];
  experience_feedback: string[];
  project_feedback: string[];
  measurable_impact_feedback: string[];
  suggestions: string[];
  diagnostics: ATSDiagnostic[];
}

/* Final interview assessment */

export interface FinalAssessment {
  interview_id: string;
  overall_score: number;
  technical_knowledge: number;
  knowledge_depth: number;
  problem_solving: number;
  communication: number;
  resume_claim_accuracy: number | null;
  strengths: string[];
  weaknesses: string[];
  summary: string;
  turns_assessed: number;
  created_at: string | null;
}

/* Voice and video interview */

export interface QuestionAudioResponse {
  turn_id: string;
  audio_base64: string;
  audio_mime_type: string;
}

export interface VoiceAnswerResponse extends InterviewAnswerResponse {
  transcribed_answer: string;
  /** Null when speech synthesis failed; the answer itself was still recorded. */
  next_question_audio_base64: string | null;
  next_question_audio_mime_type: string | null;
}

export interface VideoAnswerResponse extends InterviewAnswerResponse {
  transcribed_answer: string;
}
