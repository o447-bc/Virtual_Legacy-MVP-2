/**
 * Survey API service — submit life-events survey and check status.
 */
import { buildApiUrl } from "@/config/api";
import { fetchAuthSession } from "aws-amplify/auth";

export interface LifeEventInstance {
  name: string;
  ordinal: number;
  status?: "married" | "divorced" | "deceased";
}

export interface LifeEventInstanceGroup {
  eventKey: string;
  instances: LifeEventInstance[];
}

export interface SurveySubmitPayload {
  selectedLifeEvents: string[];
  lifeEventInstances?: LifeEventInstanceGroup[];
  customLifeEvent?: string;
}

export interface SurveySubmitResponse {
  message: string;
  assignedQuestionCount: number;
}

export interface AssignedQuestions {
  standard: string[];
  instanced: InstanceGroup[];
}

export interface InstanceGroup {
  eventKey: string;
  instanceName: string;
  instanceOrdinal: number;
  questionIds: string[];
}

export interface InstancedProgress {
  answeredKeys: string[]; // composite keys like "questionId#eventKey:ordinal"
}

export interface QuestionDetail {
  text: string;
  difficulty: number;
  questionType: string;
}

export interface SurveyStatusResponse {
  hasCompletedSurvey: boolean;
  selectedLifeEvents: string[] | null;
  surveyCompletedAt: string | null;
  lifeEventInstances: LifeEventInstanceGroup[] | null;
  assignedQuestionCount: number | null;
  assignedQuestions: AssignedQuestions | null;
  instancedProgress: InstancedProgress | null;
  questionDetails: Record<string, QuestionDetail> | null;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken?.toString();
  if (!idToken) throw new Error("No authentication token available");
  return {
    Authorization: `Bearer ${idToken}`,
    "Content-Type": "application/json",
  };
}

export async function submitSurvey(
  payload: SurveySubmitPayload
): Promise<SurveySubmitResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl("/survey/submit"), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Survey submission failed (${res.status})`);
  }
  return res.json();
}

export async function getSurveyStatus(): Promise<SurveyStatusResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(buildApiUrl("/survey/status"), { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch survey status (${res.status})`);
  }
  return res.json();
}
