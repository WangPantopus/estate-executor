/**
 * Auth0 callback page.
 *
 * The Auth0 SDK handles the callback via the proxy/middleware layer
 * at /auth/callback. This page acts as a fallback that shows a loading
 * state while the callback is being processed.
 */
export default function CallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="animate-spin mb-4 mx-auto h-8 w-8 rounded-full border-4 border-gray-200 border-t-blue-600" />
        <p className="text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}
