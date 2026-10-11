import {
  User,
  ClassroomSession,
  Question,
  ParticipationDashboard,
  StudentResponseView,
  AggregateAnalysisResponse,
  ChallengeProposalResponse,
  ChallengeStudentView,
  ReasoningCategoryResponse,
  EligibleStudentResponse,
  AuditLogResponse,
  SessionStatus,
  ChallengeStatus,
} from '../types';

const rawEnvBase = ((import.meta as any).env?.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');

export const BACKEND_ORIGIN = rawEnvBase ? rawEnvBase.replace(/\/api$/, '') : '';
export const API_BASE = rawEnvBase
  ? rawEnvBase.endsWith('/api')
    ? rawEnvBase
    : `${rawEnvBase}/api`
  : '/api';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

function notifyBackendWaking(waking: boolean) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('bst_backend_waking', { detail: { waking } }));
  }
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('bst_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const maxRetries = 3;
  let response: Response | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
        credentials: 'include',
      });

      if ([502, 503, 504].includes(response.status) && attempt < maxRetries) {
        notifyBackendWaking(true);
        await new Promise((r) => setTimeout(r, 2500 * (attempt + 1)));
        continue;
      }
      break;
    } catch (err) {
      if (attempt < maxRetries) {
        notifyBackendWaking(true);
        await new Promise((r) => setTimeout(r, 2500 * (attempt + 1)));
        continue;
      }
      notifyBackendWaking(false);
      throw new ApiError(
        0,
        'Unable to reach the server. If the backend is waking up from sleep, please wait a few seconds and try again.'
      );
    }
  }

  notifyBackendWaking(false);

  if (!response) {
    throw new ApiError(0, 'No response from server.');
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    let data;
    try {
      data = await response.json();
      if (data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(response.status, errorDetail, data);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return {} as T;
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    apiFetch<{ access_token: string; role: string; user_id: string; username: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  studentActivate: (student_id: string, new_password: string) =>
    apiFetch<{ access_token: string; role: string; user_id: string; username: string; student_id: string }>('/auth/student-activate', {
      method: 'POST',
      body: JSON.stringify({ student_id, new_password }),
    }),

  studentLogin: (student_id: string, password: string) =>
    apiFetch<{ access_token: string; role: string; user_id: string; username: string; student_id: string }>('/auth/student-login', {
      method: 'POST',
      body: JSON.stringify({ student_id, password }),
    }),

  logout: () =>
    apiFetch<{ message: string }>('/auth/logout', {
      method: 'POST',
    }),

  getMe: () => apiFetch<User>('/auth/me'),

  // Admin
  getRoster: () => apiFetch<EligibleStudentResponse[]>('/admin/roster'),

  resetStudentActivation: (studentId: string) =>
    apiFetch<EligibleStudentResponse>(`/admin/roster/${studentId}/reset-activation`, {
      method: 'POST',
    }),

  bootstrapRoster: (force_reset: boolean = false) =>
    apiFetch<{ total_eligible: number; students: { student_id: string; activation_code: string; is_activated: boolean }[] }>(
      `/admin/roster/bootstrap?force_reset=${force_reset}`,
      { method: 'POST' }
    ),

  createProfessor: (data: { username: string; email: string; password: string }) =>
    apiFetch<User>('/admin/professors', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listProfessors: () => apiFetch<User[]>('/admin/professors'),

  getAuditLogs: (limit: number = 100) => apiFetch<AuditLogResponse[]>(`/admin/audit?limit=${limit}`),

  // Sessions
  createSession: (title: string) =>
    apiFetch<ClassroomSession>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  listSessions: () => apiFetch<ClassroomSession[]>('/sessions'),

  getSession: (id: string) => apiFetch<ClassroomSession>(`/sessions/${id}`),

  updateSessionStatus: (id: string, status: SessionStatus) =>
    apiFetch<ClassroomSession>(`/sessions/${id}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),

  joinSession: (join_code: string) =>
    apiFetch<{ session_id: string; title: string; status: SessionStatus; participant_id: string }>('/sessions/join', {
      method: 'POST',
      body: JSON.stringify({ join_code }),
    }),

  getParticipation: (sessionId: string) =>
    apiFetch<ParticipationDashboard>(`/sessions/${sessionId}/participation`),

  // Questions
  createQuestion: (sessionId: string, data: any) =>
    apiFetch<Question>(`/sessions/${sessionId}/questions`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSessionQuestions: (sessionId: string) =>
    apiFetch<Question[]>(`/sessions/${sessionId}/questions`),

  getQuestion: (id: string) => apiFetch<Question>(`/questions/${id}`),

  updateQuestionStatus: (questionId: string, status: string) =>
    apiFetch<Question>(`/questions/${questionId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),

  updateQuestion: (questionId: string, data: any) =>
    apiFetch<Question>(`/questions/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteQuestion: (questionId: string) =>
    apiFetch<{ message: string }>(`/questions/${questionId}`, {
      method: 'DELETE',
    }),

  // Responses
  submitRound1: (questionId: string, data: { answer: string; confidence: number; explanation?: string; prediction?: string }) =>
    apiFetch<StudentResponseView>(`/questions/${questionId}/responses/round1`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitRound2: (questionId: string, data: { answer: string; confidence: number; changed_answer: boolean; change_reason?: string }) =>
    apiFetch<StudentResponseView>(`/questions/${questionId}/responses/round2`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitFollowUp: (questionId: string, data: { answer: string; confidence: number; explanation?: string }) =>
    apiFetch<StudentResponseView>(`/questions/${questionId}/responses/followup`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMyResponses: (questionId: string) =>
    apiFetch<StudentResponseView[]>(`/questions/${questionId}/my-responses`),

  getQuestionResults: (questionId: string) =>
    apiFetch<AggregateAnalysisResponse>(`/questions/${questionId}/results`),

  // Challenges & Reasoning
  triggerAnalysis: (questionId: string) =>
    apiFetch<{ status: string; categories_count: number; challenge_id: string }>(`/questions/${questionId}/analyze`, {
      method: 'POST',
    }),

  getChallenge: (questionId: string) =>
    apiFetch<ChallengeProposalResponse | ChallengeStudentView>(`/questions/${questionId}/challenge`),

  reviewChallenge: (challengeId: string, data: { status: ChallengeStatus; edited_text?: string; instructor_notes?: string }) =>
    apiFetch<ChallengeProposalResponse>(`/challenges/${challengeId}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getCategories: (questionId: string) =>
    apiFetch<ReasoningCategoryResponse[]>(`/questions/${questionId}/categories`),

  updateCategory: (categoryId: string, data: { title?: string; description?: string; is_misconception?: boolean; is_approved?: boolean }) =>
    apiFetch<ReasoningCategoryResponse>(`/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};
