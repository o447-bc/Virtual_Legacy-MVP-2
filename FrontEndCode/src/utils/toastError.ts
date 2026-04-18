/**
 * Toast error wrappers that report errors to the backend.
 *
 * Use these instead of calling toast.error() or toast({variant: "destructive"})
 * directly. They show the same UI notification AND silently report the error
 * to POST /log-error for centralized monitoring.
 *
 * Requirements: 3.1
 */
import { toast } from '@/components/ui/sonner';
import { reportError } from '@/services/errorReporter';

/**
 * Show a Sonner toast.error() and report the error to the backend.
 *
 * @param message  The error message shown to the user
 * @param component  The component/page name where the error occurred
 */
export function toastError(message: string, component: string): void {
  toast.error(message);
  reportError({
    errorMessage: message,
    component,
    url: window.location.href,
    metadata: {
      userAgent: navigator.userAgent,
      route: window.location.pathname,
    },
  });
}
