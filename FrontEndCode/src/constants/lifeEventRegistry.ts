/**
 * Canonical Life Event Key Registry
 *
 * Single source of truth for all valid Life_Event_Keys used across the
 * admin tool, survey UI, and assignment Lambda. Any new life event must
 * be added here first.
 */

export interface LifeEventKeyInfo {
  key: string;
  label: string;
  category: string;
  isInstanceable: boolean;
  instancePlaceholder?: string;
}

export const LIFE_EVENT_CATEGORIES = [
  'Core Relationship & Family',
  'Education & Early Life',
  'Career & Professional',
  'Health & Resilience',
  'Relocation & Transitions',
  'Spiritual, Creative & Legacy',
  'Other',
  'Status-derived',
] as const;

export type LifeEventCategory = (typeof LIFE_EVENT_CATEGORIES)[number];

export const LIFE_EVENT_REGISTRY: LifeEventKeyInfo[] = [
  // Core Relationship & Family
  { key: 'got_married', label: 'Got married or entered a long-term partnership', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{spouse_name}' },
  { key: 'had_children', label: 'Had children', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{child_name}' },
  { key: 'became_grandparent', label: 'Became a grandparent', category: 'Core Relationship & Family', isInstanceable: false },
  { key: 'death_of_child', label: 'Death of a child', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{deceased_name}' },
  { key: 'death_of_parent', label: 'Death of a parent', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{deceased_name}' },
  { key: 'death_of_sibling', label: 'Death of a sibling or close family member', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{deceased_name}' },
  { key: 'death_of_friend_mentor', label: 'Death of a close friend or mentor', category: 'Core Relationship & Family', isInstanceable: true, instancePlaceholder: '{deceased_name}' },
  { key: 'estranged_family_member', label: 'Became estranged from a family member', category: 'Core Relationship & Family', isInstanceable: false },
  { key: 'infertility_or_pregnancy_loss', label: 'Experienced infertility or pregnancy loss', category: 'Core Relationship & Family', isInstanceable: false },
  { key: 'raised_child_special_needs', label: 'Raised a child with special needs', category: 'Core Relationship & Family', isInstanceable: false },
  { key: 'falling_out_close_friend', label: 'Had a significant falling out with a close friend', category: 'Core Relationship & Family', isInstanceable: false },

  // Education & Early Life
  { key: 'graduated_high_school', label: 'Graduated from high school', category: 'Education & Early Life', isInstanceable: false },
  { key: 'graduated_college', label: 'Graduated from college or university', category: 'Education & Early Life', isInstanceable: false },
  { key: 'graduate_degree', label: 'Earned a graduate or professional degree', category: 'Education & Early Life', isInstanceable: false },
  { key: 'studied_abroad', label: 'Studied abroad or had a formative travel experience', category: 'Education & Early Life', isInstanceable: false },
  { key: 'influential_mentor', label: 'Had a teacher or mentor who changed your trajectory', category: 'Education & Early Life', isInstanceable: false },

  // Career & Professional
  { key: 'first_job', label: 'Started your first real job', category: 'Career & Professional', isInstanceable: false },
  { key: 'career_change', label: 'Changed careers or industries', category: 'Career & Professional', isInstanceable: false },
  { key: 'started_business', label: 'Started your own business or became self-employed', category: 'Career & Professional', isInstanceable: false },
  { key: 'got_fired', label: 'Got fired or laid off', category: 'Career & Professional', isInstanceable: false },
  { key: 'retired', label: 'Retired from your primary career', category: 'Career & Professional', isInstanceable: false },
  { key: 'became_mentor', label: 'Became a mentor or teacher', category: 'Career & Professional', isInstanceable: false },

  // Health & Resilience
  { key: 'serious_illness', label: 'Overcame a serious illness or injury', category: 'Health & Resilience', isInstanceable: false },
  { key: 'mental_health_challenge', label: 'Dealt with a mental health challenge', category: 'Health & Resilience', isInstanceable: false },
  { key: 'caregiver', label: 'Cared for an aging or ill family member', category: 'Health & Resilience', isInstanceable: false },
  { key: 'addiction_recovery', label: 'Went through addiction or recovery', category: 'Health & Resilience', isInstanceable: false },
  { key: 'financial_hardship', label: 'Experienced financial hardship or bankruptcy', category: 'Health & Resilience', isInstanceable: false },
  { key: 'major_legal_issue', label: 'Went through a major legal issue', category: 'Health & Resilience', isInstanceable: false },

  // Relocation & Transitions
  { key: 'moved_city', label: 'Moved to a new city or state', category: 'Relocation & Transitions', isInstanceable: false },
  { key: 'immigrated', label: 'Immigrated to a new country', category: 'Relocation & Transitions', isInstanceable: false },
  { key: 'lived_abroad', label: 'Lived abroad for an extended period', category: 'Relocation & Transitions', isInstanceable: false },
  { key: 'learned_second_language', label: 'Learned a second language or became bilingual', category: 'Relocation & Transitions', isInstanceable: false },

  // Spiritual, Creative & Legacy
  { key: 'spiritual_awakening', label: 'Had a spiritual awakening or deepened your faith', category: 'Spiritual, Creative & Legacy', isInstanceable: false },
  { key: 'changed_religion', label: 'Left or changed your religion', category: 'Spiritual, Creative & Legacy', isInstanceable: false },
  { key: 'creative_work', label: 'Completed a creative work you are proud of', category: 'Spiritual, Creative & Legacy', isInstanceable: false },
  { key: 'major_award', label: 'Received a major award or public recognition', category: 'Spiritual, Creative & Legacy', isInstanceable: false },
  { key: 'experienced_discrimination', label: 'Experienced racism, discrimination, or a civil rights moment', category: 'Spiritual, Creative & Legacy', isInstanceable: false },

  // Other
  { key: 'military_service', label: 'Served in the military', category: 'Other', isInstanceable: false },
  { key: 'survived_disaster', label: 'Survived a natural disaster or major crisis', category: 'Other', isInstanceable: false },
  { key: 'near_death', label: 'Had a brush with death or near-death experience', category: 'Other', isInstanceable: false },
  { key: 'act_of_kindness', label: 'Experienced a life-changing act of kindness', category: 'Other', isInstanceable: false },

  // Status-derived (virtual — generated from got_married instance statuses)
  { key: 'spouse_divorced', label: 'Spouse divorced/separated', category: 'Status-derived', isInstanceable: false },
  { key: 'spouse_deceased', label: 'Spouse passed away', category: 'Status-derived', isInstanceable: false },
  { key: 'spouse_still_married', label: 'Spouse still married/together', category: 'Status-derived', isInstanceable: false },
];

/** All valid Life_Event_Key strings */
export const ALL_LIFE_EVENT_KEYS: string[] = LIFE_EVENT_REGISTRY.map(e => e.key);

/** Keys that support question instancing (per-person question stamping) */
export const INSTANCEABLE_KEYS: string[] = LIFE_EVENT_REGISTRY
  .filter(e => e.isInstanceable)
  .map(e => e.key);

/** Valid placeholder tokens for instanceable questions */
export const VALID_PLACEHOLDERS = ['{spouse_name}', '{child_name}', '{deceased_name}'] as const;

/** Maps each instanceable key to its placeholder token */
export const INSTANCEABLE_KEY_TO_PLACEHOLDER: Record<string, string> = Object.fromEntries(
  LIFE_EVENT_REGISTRY
    .filter(e => e.isInstanceable && e.instancePlaceholder)
    .map(e => [e.key, e.instancePlaceholder!])
);

/** Helper: check if a key is a valid Life_Event_Key */
export function isValidLifeEventKey(key: string): boolean {
  return ALL_LIFE_EVENT_KEYS.includes(key);
}

/** Helper: get registry entries grouped by category */
export function getRegistryByCategory(): Record<string, LifeEventKeyInfo[]> {
  return LIFE_EVENT_REGISTRY.reduce((acc, entry) => {
    if (!acc[entry.category]) {
      acc[entry.category] = [];
    }
    acc[entry.category].push(entry);
    return acc;
  }, {} as Record<string, LifeEventKeyInfo[]>);
}
