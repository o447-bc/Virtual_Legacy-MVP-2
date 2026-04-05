/**
 * Admin API service — typed functions for all admin tool API calls.
 */
import { buildApiUrl } from "@/config/api";
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
  active: boolean;
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
