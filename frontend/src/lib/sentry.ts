/**
 * Sentry initialization for the frontend.
 *
 * Initializes Sentry error tracking and performance monitoring.
 * If NEXT_PUBLIC_SENTRY_DSN is not set, Sentry is silently disabled.
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

let initialized = false;

export function initSentry(): void {
  if (initialized || !SENTRY_DSN) return;

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NEXT_PUBLIC_APP_ENV || "development",
    release: `estate-executor-frontend@${process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0"}`,

    // Performance monitoring
    tracesSampleRate: parseFloat(
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || "0.1"
    ),

    // Session replay for debugging (only in production).
    // replaysOnErrorSampleRate is intentionally low (10%) to limit PII exposure
    // in replays - estate data includes SSNs, asset values, and beneficiary PII.
    replaysSessionSampleRate: 0.0,
    replaysOnErrorSampleRate: 0.1,

    integrations: [
      // Mask all input fields in session replays to prevent capturing sensitive
      // estate data (SSNs, asset values, beneficiary information, etc.).
      Sentry.replayIntegration({
        maskAllInputs: true,
        maskAllText: false,
      }),
    ],

    // Filter noisy errors
    ignoreErrors: [
      // Browser extensions
      "ResizeObserver loop",
      // Network errors (user is offline)
      "Failed to fetch",
      "NetworkError",
      "Load failed",
      // Auth0 redirects
      "NEXT_REDIRECT",
    ],

    beforeSend(event) {
      // Strip sensitive data from breadcrumbs
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map((breadcrumb) => {
          if (breadcrumb.category === "xhr" || breadcrumb.category === "fetch") {
            // Remove auth headers from network breadcrumbs
            if (breadcrumb.data) {
              delete breadcrumb.data["Authorization"];
              delete breadcrumb.data["Cookie"];
            }
          }
          return breadcrumb;
        });
      }
      return event;
    },
  });

  initialized = true;
}

/**
 * Report an error to Sentry with optional context.
 */
export function captureError(
  error: Error,
  context?: Record<string, unknown>
): void {
  if (!SENTRY_DSN) {
    console.error("[Sentry disabled]", error, context);
    return;
  }

  if (context) {
    Sentry.withScope((scope) => {
      Object.entries(context).forEach(([key, value]) => {
        scope.setExtra(key, value);
      });
      Sentry.captureException(error);
    });
  } else {
    Sentry.captureException(error);
  }
}

/**
 * Set user context for Sentry events.
 */
export function setSentryUser(user: {
  id: string;
  email?: string;
  firmId?: string;
}): void {
  if (!SENTRY_DSN) return;
  Sentry.setUser({ id: user.id, email: user.email });
  if (user.firmId) {
    Sentry.setTag("firm_id", user.firmId);
  }
}
