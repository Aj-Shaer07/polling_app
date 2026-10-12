export type UserRole = 'ADMIN' | 'PROFESSOR' | 'STUDENT';

export interface User {
  id: string;
  username: string;
  email?: string | null;
  role: UserRole;
  student_id?: string | null;
  is_active: boolean;
}

export type SessionStatus =
  | 'DRAFT'
  | 'OPEN_ROUND_1'
  | 'ANALYZING'
  | 'CHALLENGE_PENDING'
  | 'OPEN_ROUND_2'
  | 'FOLLOW_UP'
  | 'COMPLETED'
  | 'ARCHIVED';

export type QuestionType =
  | 'FACTUAL'
  | 'SUBJECTIVE'
  | 'PREDICTION'
  | 'OPEN_REASONING';

export interface Question {
  id: string;
  session_id: string;
  question_text: string;
  question_type: QuestionType;
  reference_answer?: string | null;
  accepted_reasoning?: string | null;
  choices?: string[] | null;
  confidence_required: boolean;
  reasoning_required: boolean;
  prediction_enabled: boolean;
  order_index: number;
  is_follow_up: boolean;
  status?: string;
  created_at: string;
}

export interface StudentParticipationStatus {
  student_id: string;
  joined: boolean;
  round_1_submitted: boolean;
  round_1_submitted_at?: string | null;
  round_2_submitted: boolean;
  round_2_submitted_at?: string | null;
  follow_up_submitted: boolean;
  follow_up_submitted_at?: string | null;
}

export interface ParticipationDashboard {
  eligible_total: number;
  joined_count: number;
  round_1_answered: number;
  round_1_pending: number;
  round_2_answered: number;
  round_2_pending: number;
  follow_up_answered: number;
  follow_up_pending: number;
  students: StudentParticipationStatus[];
}

export interface ClassroomSession {
  id: string;
  title: string;
  join_code: string;
  professor_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  questions?: Question[];
  participation?: ParticipationDashboard;
}

export interface AnswerDistributionItem {
  answer: string;
  count: number;
  percentage: number;
  average_confidence: number;
  is_reference_correct?: boolean | null;
}

export interface ConfidenceDistributionItem {
  confidence: number;
  count: number;
  percentage: number;
}

export interface BeliefTransitionItem {
  from_answer: string;
  to_answer: string;
  count: number;
  percentage: number;
  avg_initial_confidence: number;
  avg_revised_confidence: number;
  sample_change_reasons: string[];
}

export interface QuestionStudentParticipationItem {
  student_id: string;
  joined: boolean;
  round_1_submitted: boolean;
  round_1_submitted_at?: string | null;
  round_2_submitted: boolean;
  round_2_submitted_at?: string | null;
}

export interface AggregateAnalysisResponse {
  question_id: string;
  round_1_total: number;
  round_2_total: number;
  round_1_distributions: AnswerDistributionItem[];
  round_2_distributions: AnswerDistributionItem[];
  confidence_distributions_round_1: ConfidenceDistributionItem[];
  confidence_distributions_round_2: ConfidenceDistributionItem[];
  belief_transitions: BeliefTransitionItem[];
  student_participation?: QuestionStudentParticipationItem[];
  instructor_insight?: string | null;
  ai_summary?: string | null;
}

export interface ReasoningCategoryResponse {
  id: string;
  question_id: string;
  round_number: number;
  title: string;
  description: string;
  is_misconception: boolean;
  sample_explanations: string[];
  response_count: number;
  percentage: number;
  is_ai_proposed: boolean;
  is_approved: boolean;
  created_at: string;
}

export type ChallengeStatus = 'PROPOSED' | 'APPROVED' | 'EDITED' | 'REJECTED';

export interface ChallengeProposalResponse {
  id: string;
  question_id: string;
  challenge_type: string;
  challenge_text: string;
  targeted_reasoning_pattern: string;
  relevance_evidence: string;
  learning_objective: string;
  assumptions_and_uncertainties: string;
  status: ChallengeStatus;
  edited_text?: string | null;
  instructor_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChallengeStudentView {
  id: string;
  challenge_type: string;
  challenge_text: string;
  targeted_reasoning_pattern?: string | null;
}

export interface StudentResponseView {
  id: string;
  round_number: number;
  answer: string;
  confidence: number;
  explanation?: string | null;
  prediction?: string | null;
  changed_answer?: boolean | null;
  change_reason?: string | null;
  submitted_at: string;
}

export interface EligibleStudentResponse {
  id: number;
  student_id: string;
  is_activated: boolean;
  activated_at?: string | null;
  created_at: string;
}

export interface AuditLogResponse {
  id: number;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  details?: any;
  ip_address?: string | null;
  created_at: string;
}
