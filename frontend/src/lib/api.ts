import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// On 401, clear session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// ─── Auth ──────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  updateMe: (data: Record<string, unknown>) => api.patch('/auth/me', data),
  // Admin
  listUsers: () => api.get('/auth/admin/users'),
  createUser: (data: Record<string, unknown>) => api.post('/auth/admin/users', data),
  toggleUserActive: (userId: string) => api.patch(`/auth/admin/users/${userId}/toggle-active`),
};

// ─── Resumes ───────────────────────────────────────────────────────────────

export const resumeApi = {
  upload: (file: File, isPrimary = false) => {
    const form = new FormData();
    form.append('file', file);
    form.append('is_primary', String(isPrimary));
    return api.post('/resumes/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  list: () => api.get('/resumes/'),
  get: (id: string) => api.get(`/resumes/${id}`),
  delete: (id: string) => api.delete(`/resumes/${id}`),
  generateVersion: (data: Record<string, unknown>) => api.post('/resumes/versions/generate', data),
  downloadVersion: (versionId: string, fmt: 'pdf' | 'docx') =>
    api.get(`/resumes/versions/${versionId}/download/${fmt}`, { responseType: 'blob' }),
};

// ─── Jobs ──────────────────────────────────────────────────────────────────

export const jobsApi = {
  list: (params?: Record<string, unknown>) => api.get('/jobs/', { params }),
  get: (id: string) => api.get(`/jobs/${id}`),
  search: (data: Record<string, unknown>) => api.post('/jobs/search', data),
  searchStatus: (taskId: string) => api.get(`/jobs/search/status/${taskId}`),
  recent: (hours = 6) => api.get('/jobs/recent/new', { params: { hours } }),
};

// ─── Scoring ───────────────────────────────────────────────────────────────

export const scoringApi = {
  scoreJob: (jobId: string, resumeId: string) =>
    api.post('/scoring/score', { job_id: jobId, resume_id: resumeId }),
  batchScore: (jobIds: string[], resumeId: string) =>
    api.post('/scoring/score/batch', { job_ids: jobIds, resume_id: resumeId }),
  matches: () => api.get('/scoring/matches'),
};

// ─── Applications ──────────────────────────────────────────────────────────

export const applicationsApi = {
  create: (data: Record<string, unknown>) => api.post('/applications/', data),
  list: (status?: string) => api.get('/applications/', { params: status ? { status } : {} }),
  get: (id: string) => api.get(`/applications/${id}`),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/applications/${id}`, data),
  delete: (id: string) => api.delete(`/applications/${id}`),
};

// ─── Cover Letters ─────────────────────────────────────────────────────────

export const coverLetterApi = {
  generate: (data: Record<string, unknown>) => api.post('/cover-letters/generate', data),
  list: () => api.get('/cover-letters/'),
  download: (id: string, fmt: 'pdf' | 'docx') =>
    api.get(`/cover-letters/${id}/download/${fmt}`, { responseType: 'blob' }),
};

// ─── Outreach ──────────────────────────────────────────────────────────────

export const outreachApi = {
  generate: (data: Record<string, unknown>) => api.post('/outreach/generate', data),
  list: () => api.get('/outreach/'),
};

// ─── Interview Prep ────────────────────────────────────────────────────────

export const interviewPrepApi = {
  generate: (jobId: string, resumeId: string) =>
    api.post(`/interview-prep/generate?job_id=${jobId}&resume_id=${resumeId}`),
};

// ─── Automation ────────────────────────────────────────────────────────────

export const automationApi = {
  start: (jobId: string, resumeId: string) =>
    api.post('/automation/start', null, { params: { job_id: jobId, resume_id: resumeId } }),
  status: (sessionId: string) => api.get(`/automation/status/${sessionId}`),
  confirm: (sessionId: string) => api.post(`/automation/confirm/${sessionId}`),
  cancel: (sessionId: string) => api.post(`/automation/cancel/${sessionId}`),
};
