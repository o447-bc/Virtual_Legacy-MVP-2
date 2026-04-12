// ---------------------------------------------------------------------------
// Psych Test Type Definitions
// Matches SamLambda/schemas/psych-test-definition.schema.json
// ---------------------------------------------------------------------------

/** Consent screen shown before test questions */
export interface ConsentBlock {
  title: string;
  bodyText: string;
  requiredCheckboxLabel: string;
}

/** A single question within a test definition */
export interface Question {
  questionId: string;
  text: string;
  responseType: 'likert5' | 'bipolar5' | 'multipleChoice';
  options: string[];
  reverseScored: boolean;
  scoringKey: string;
  groupByFacet: string;
  pageBreakAfter: boolean;
  accessibilityHint: string;
  videoPromptFrequency?: number;
}

/** Threshold entry within a scoring rule */
export interface ThresholdEntry {
  min: number;
  max: number;
  label: string;
}

/** Scoring rule for a domain or facet */
export interface ScoringRule {
  formula: string;
  thresholds: ThresholdEntry[];
  lookupTables?: Record<string, number[]>;
}

/** Source reference for composite rules */
export interface CompositeSource {
  testId: string;
  domain: string;
}

/** Rule for combining scores across domains or tests */
export interface CompositeRule {
  sources: CompositeSource[];
  formula: string;
}

/** Score-range-to-narrative mapping entry */
export interface InterpretationEntry {
  min: number;
  max: number;
  text: string;
}

/** Optional AI narrative generation configuration */
export interface BedrockConfig {
  useBedrock: boolean;
  maxTokens: number;
  temperature: number;
  cacheResultsForDays: number;
}

/** Full test definition matching the JSON schema */
export interface TestDefinition {
  testId: string;
  testName: string;
  description: string;
  version: string;
  previousVersionMapping?: Record<string, string>;
  estimatedMinutes: number;
  consentBlock: ConsentBlock;
  disclaimerText: string;
  questions: Question[];
  scoringRules: Record<string, ScoringRule>;
  compositeRules: Record<string, CompositeRule>;
  interpretationTemplates: Record<string, InterpretationEntry[]>;
  domainDescriptions?: Record<string, string>;
  bedrockPromptTemplate?: string;
  bedrockConfig?: BedrockConfig;
  videoPromptTrigger: string;
  saveProgressEnabled: boolean;
  analyticsEnabled: boolean;
  exportFormats: string[];
}

// ---------------------------------------------------------------------------
// API Response Types
// ---------------------------------------------------------------------------

/** Lightweight test info returned by the list endpoint */
export interface PsychTest {
  testId: string;
  testName: string;
  description: string;
  estimatedMinutes: number;
  status: string;
  version: string;
  completedAt?: string;
}

/** A single question response from the user */
export interface QuestionResponse {
  questionId: string;
  answer: number;
}

/** Saved in-progress test state */
export interface TestProgress {
  responses: QuestionResponse[];
  currentQuestionIndex: number;
  updatedAt: string;
}

/** Score entry for a domain or facet */
export interface ScoreEntry {
  raw: number;
  normalized: number;
  label: string;
}

/** Complete scored test result */
export interface TestResult {
  userId: string;
  testId: string;
  version: string;
  timestamp: string;
  domainScores: Record<string, ScoreEntry>;
  facetScores: Record<string, ScoreEntry>;
  compositeScores: Record<string, ScoreEntry>;
  thresholdClassifications: Record<string, string>;
  narrativeText: string;
  narrativeSource: 'bedrock' | 'template';
  exportFormats: string[];
}

/** Response from the export endpoint */
export interface ExportResponse {
  downloadUrl: string;
  expiresIn: number;
}
