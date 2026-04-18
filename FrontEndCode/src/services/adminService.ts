/**
 * Admin API service — typed functions for all admin tool API calls.
 */
import { API_CONFIG, buildApiUrl } from "@/config/api";
import { fetchAuthSession } from "aws-amplify/auth";

// Admin endpoint paths
const ADMIN_ENDPOINTS = {
  QUESTIONS: "/admin/questions",
  QUESTIONS_BATCH: "/admin/questions/batch",
  SIMULATE: "/admin/simulate",
  COVERAGE: "/admin/coverage",
  THEMES: "/admin/themes",
  STATS: "/admin/stats",
  EXPORT: "/admin/export",
  MIGRATE: "/admin/migrate",
};

// Types
export interface QuestionRecord {
  questionId: string;
  questionType: string;
  themeName: string;
  difficulty: number;
  Valid: number;
  questionText: string;
  requiredLifeEvents: string[];
  isInstanceable: boolean;
  instancePlaceholder: string;
  lastModifiedBy: string;
  lastModifiedAt: string;
}

export interface StatsData {
  totalQuestions: number;
  validQuestions: number;
  invalidQuestions: number;
  questionTypes: number;
  difficultyLevels: number;
  zeroCoverageKeys: number;
  instanceableQuestions: number;
  needsMigration: number;
  typeToTheme: Record<string, string>;
  grid: Record<string, Record<string, number>>;
  difficultyTotals: Record<string, number>;
  grandTotal: number;
}

export interface CoverageData {
  coverage: Record<
    string,
    { total: number; instanceable: number; nonInstanceable: number }
  >;
  universalCount: number;
}

export interface SimulateResult {
  totalCount: number;
  byQuestionType: Record<
    string,
    { count: number; questions: QuestionRecord[] }
  >;
}

// Helper to get auth headers
async function getAuthHeaders(): Promise<Record<string, string>> {
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken?.toString();
  if (!idToken) throw new Error("No authentication token available");
  return {
    Authorization: `Bearer ${idToken}`,
    "Content-Type": "application/json",
  };
}

// --- Questions CRUD ---

export async function fetchQuestions(): Promise<QuestionRecord[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.QUESTIONS), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch questions (${res.status})`);
  }
  const data = await res.json();
  return data.questions;
}

export async function createQuestion(
  question: Partial<QuestionRecord>
): Promise<{ questionId: string; message: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.QUESTIONS), {
    method: "POST",
    headers,
    body: JSON.stringify(question),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to create question (${res.status})`);
  }
  return res.json();
}

export async function updateQuestion(
  questionId: string,
  updates: Partial<QuestionRecord>
): Promise<{ message: string; questionId: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${ADMIN_ENDPOINTS.QUESTIONS}/${encodeURIComponent(questionId)}`),
    {
      method: "PUT",
      headers,
      body: JSON.stringify(updates),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to update question (${res.status})`);
  }
  return res.json();
}

// --- Batch Import ---

export async function batchImport(payload: {
  questionType: string;
  Difficulty: number;
  requiredLifeEvents: string[];
  isInstanceable: boolean;
  instancePlaceholder: string;
  questions: string[];
}): Promise<{ message: string; imported: number; questionIds: string[] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.QUESTIONS_BATCH), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Batch import failed (${res.status})`);
  }
  return res.json();
}

// --- Simulate ---

export async function simulate(
  selectedLifeEvents: string[]
): Promise<SimulateResult> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.SIMULATE), {
    method: "POST",
    headers,
    body: JSON.stringify({ selectedLifeEvents }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Simulation failed (${res.status})`);
  }
  return res.json();
}

// --- Coverage ---

export async function fetchCoverage(): Promise<CoverageData> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.COVERAGE), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch coverage (${res.status})`);
  }
  return res.json();
}

// --- Stats ---

export async function fetchStats(): Promise<StatsData> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.STATS), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch stats (${res.status})`);
  }
  return res.json();
}

// --- Themes ---

export async function applyThemeDefaults(
  questionType: string,
  settings: {
    requiredLifeEvents: string[];
    isInstanceable: boolean;
    instancePlaceholder: string;
  }
): Promise<{ message: string; questionsUpdated: number }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${ADMIN_ENDPOINTS.THEMES}/${encodeURIComponent(questionType)}`),
    {
      method: "PUT",
      headers,
      body: JSON.stringify(settings),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to apply theme defaults (${res.status})`);
  }
  return res.json();
}

// --- Export ---

export async function exportQuestions(
  format: "csv" | "json"
): Promise<string | QuestionRecord[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(ADMIN_ENDPOINTS.EXPORT, { format }),
    { headers }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Export failed (${res.status})`);
  }
  if (format === "csv") {
    return res.text();
  }
  const data = await res.json();
  return data.questions;
}

// --- Migration ---

export async function runMigration(): Promise<{
  message: string;
  updated: number;
  skipped: number;
}> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(ADMIN_ENDPOINTS.MIGRATE), {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Migration failed (${res.status})`);
  }
  return res.json();
}

// --- Settings Types ---

export interface SettingItem {
  settingKey: string;
  value: string;
  valueType: 'string' | 'integer' | 'float' | 'boolean' | 'text' | 'model';
  section: string;
  label: string;
  description: string;
  updatedAt: string;
  updatedBy: string;
}

export interface SettingsResponse {
  settings: Record<string, SettingItem[]>;
}

export interface UpdateSettingResponse {
  message: string;
  updatedAt: string;
  updatedBy: string;
}

export interface BedrockModel {
  modelId: string;
  modelName: string;
  providerName: string;
  inputPricePerKToken: number | null;
  outputPricePerKToken: number | null;
}

// --- Settings CRUD ---

export async function fetchSettings(): Promise<SettingsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_SETTINGS), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch settings (${res.status})`);
  }
  return res.json();
}

export async function updateSetting(settingKey: string, value: string): Promise<UpdateSettingResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_SETTINGS}/${encodeURIComponent(settingKey)}`),
    {
      method: "PUT",
      headers,
      body: JSON.stringify({ value }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to update setting (${res.status})`);
  }
  return res.json();
}

// --- Bedrock Models ---

export async function fetchBedrockModels(): Promise<BedrockModel[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_BEDROCK_MODELS), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch Bedrock models (${res.status})`);
  }
  const data = await res.json();
  return data.models;
}


// --- Feedback Report Types ---

export interface FeedbackReport {
  reportId: string;
  reportType: 'bug' | 'feature';
  subject: string;
  description: string;
  userEmail: string;
  userName: string;
  userId: string;
  submittedAt: string;
  status: 'active' | 'archived';
  aiClassification: 'bug' | 'feature_request' | 'unclassified';
  aiSummary: string;
}

// --- Feedback Submission (user-facing, requires auth) ---

export async function submitFeedback(payload: {
  reportType: 'bug' | 'feature';
  subject: string;
  description: string;
  userEmail: string;
  userName: string;
}): Promise<{ status: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SUBMIT_FEEDBACK), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to submit feedback (${res.status})`);
  }
  return res.json();
}

// --- Feedback Admin ---

export async function fetchFeedbackReports(): Promise<FeedbackReport[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_FEEDBACK), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch feedback reports (${res.status})`);
  }
  const data = await res.json();
  return data.reports;
}

export async function fetchFeedbackReport(reportId: string): Promise<FeedbackReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_FEEDBACK}/${encodeURIComponent(reportId)}`),
    { headers }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch feedback report (${res.status})`);
  }
  const data = await res.json();
  return data.report;
}

export async function updateFeedbackStatus(
  reportId: string,
  status: 'active' | 'archived'
): Promise<{ message: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_FEEDBACK}/${encodeURIComponent(reportId)}`),
    {
      method: "PATCH",
      headers,
      body: JSON.stringify({ status }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to update feedback status (${res.status})`);
  }
  return res.json();
}

export async function deleteFeedbackReport(reportId: string): Promise<{ message: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_FEEDBACK}/${encodeURIComponent(reportId)}`),
    { method: "DELETE", headers }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to delete feedback report (${res.status})`);
  }
  return res.json();
}
