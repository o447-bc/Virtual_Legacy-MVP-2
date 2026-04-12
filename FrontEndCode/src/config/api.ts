// API Configuration
// Environment variables are loaded from .env file (see .env.example for template)
// Build-time env vars are injected by GitHub Actions CI workflow

// Validate API base URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
if (!apiBaseUrl) {
  throw new Error(
    'Missing required environment variable: VITE_API_BASE_URL\n' +
    'Please copy .env.example to .env and fill in your API Gateway URL.'
  );
}

export const API_CONFIG = {
  BASE_URL: apiBaseUrl,
  
  ENDPOINTS: {
    QUESTION_TYPE_DATA: '/functions/questionDbFunctions/typedata',
    UNANSWERED_QUESTIONS: '/functions/questionDbFunctions/unanswered',
    QUESTION_TYPES: '/functions/questionDbFunctions/types',
    VALID_QUESTIONS_COUNT: '/functions/questionDbFunctions/validcount',
    GET_QUESTION_BY_ID: '/functions/questionDbFunctions/question',
    UNANSWERED_QUESTIONS_WITH_TEXT: '/functions/questionDbFunctions/unansweredwithtext',
    PROGRESS_SUMMARY: '/functions/questionDbFunctions/progress-summary',
    PROGRESS_SUMMARY_2: '/functions/questionDbFunctions/progress-summary-2',
    INITIALIZE_PROGRESS: '/functions/questionDbFunctions/initialize-progress',
    INCREMENT_LEVEL: '/functions/questionDbFunctions/increment-level',
    INCREMENT_LEVEL_2: '/functions/questionDbFunctions/increment-level-2',
    TOTAL_VALID_QUESTIONS: '/functions/questionDbFunctions/totalvalidcount',
    USER_COMPLETED_COUNT: '/functions/questionDbFunctions/usercompletedcount',
    UPLOAD_VIDEO: '/functions/videoFunctions/upload',
    GET_UPLOAD_URL: '/functions/videoFunctions/get-upload-url',
    PROCESS_VIDEO: '/functions/videoFunctions/process-video',
    SEND_INVITE: '/invites/send',
    GET_MAKER_VIDEOS: '/videos/maker',
    GET_AUDIO_SUMMARY_FOR_VIDEO: '/functions/questionDbFunctions/get-audio-summary-for-video',
    BILLING_STATUS: '/billing/status',
    BILLING_CREATE_CHECKOUT: '/billing/create-checkout-session',
    BILLING_PORTAL: '/billing/portal',
    BILLING_APPLY_COUPON: '/billing/apply-coupon',
    BILLING_PLANS: '/billing/plans',

    // Data Retention & Lifecycle
    DATA_EXPORT_REQUEST: '/data/export-request',
    DATA_GDPR_EXPORT: '/data/gdpr-export',
    DATA_EXPORT_STATUS: '/data/export-status',
    ACCOUNT_DELETE_REQUEST: '/account/delete-request',
    ACCOUNT_CANCEL_DELETION: '/account/cancel-deletion',
    ACCOUNT_DELETION_STATUS: '/account/deletion-status',
    LEGACY_PROTECTION_REQUEST: '/legacy/protection-request',
    ADMIN_STORAGE_REPORT: '/admin/storage-report',

    // Psychological Testing
    PSYCH_TESTS_LIST: '/psych-tests/list',
    PSYCH_TEST_DEFINITION: '/psych-tests',
    PSYCH_TESTS_SCORE: '/psych-tests/score',
    PSYCH_TESTS_PROGRESS_SAVE: '/psych-tests/progress/save',
    PSYCH_TESTS_PROGRESS_GET: '/psych-tests/progress',
    PSYCH_TESTS_EXPORT: '/psych-tests/export',
    PSYCH_TESTS_RESULTS: '/psych-tests/results',
    PSYCH_TESTS_ADMIN_UPDATE: '/psych-tests/admin/update',
  }
};

// Helper function to build full URL
export const buildApiUrl = (endpoint: string, params?: Record<string, string>) => {
  let url = `${API_CONFIG.BASE_URL}${endpoint}`;
  
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }
  
  return url;
};