/**
 * Fire-and-forget event tracking.
 * Currently logs to console. Replace the body with your analytics
 * provider's SDK call (e.g., gtag, mixpanel.track, amplitude.logEvent).
 */
export function trackEvent(name: string, properties?: Record<string, string | number | boolean>): void {
  try {
    // Future: replace with provider SDK call
    if (typeof window !== 'undefined' && window.console) {
      console.debug('[analytics]', name, properties);
    }
  } catch {
    // Non-blocking — swallow errors
  }
}
