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

export interface InterviewStateResponse {
  interview_id: string;
  candidate_id: string;
  resume_id: string | null;
  objective: string;
  difficulty: QuestionDifficulty;
  current_question: GeneratedQuestion | null;
  knowledge_state: CandidateKnowledgeState;
  turns: InterviewTurn[];
}
