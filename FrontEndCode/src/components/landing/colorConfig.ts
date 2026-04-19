// === ACCENT COLOR TOGGLE ===
// To revert to the original purple palette, change USE_WARM_ACCENT to false.
// That's it — one line, all components fall back to legacy-purple/legacy-navy.
const USE_WARM_ACCENT = true;

export const PRIMARY_CTA_CLASSES = USE_WARM_ACCENT
  ? 'bg-legacy-warmAccent hover:bg-legacy-warmAccentHover text-white'
  : 'bg-legacy-purple hover:bg-legacy-navy text-white';

export const STEP_NUMBER_CLASSES = USE_WARM_ACCENT
  ? 'text-legacy-warmAccent font-bold text-2xl'
  : 'text-legacy-purple font-bold text-2xl';

export const CLOSING_CTA_GRADIENT = USE_WARM_ACCENT
  ? 'bg-gradient-to-br from-legacy-lightPurple to-amber-50'
  : 'bg-gradient-to-br from-legacy-lightPurple to-white';
