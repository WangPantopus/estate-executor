import Link from "next/link";
import { auth0 } from "@/lib/auth0";

export default async function Home() {
  const session = await auth0.getSession();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Estate Executor OS
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Coordination Operating System for Estate Administration
        </p>

        <div className="mt-8 flex gap-4 justify-center">
          {session ? (
            <>
              <span className="text-sm text-muted-foreground">
                Signed in as {session.user.email}
              </span>
              <Link
                href="/matters"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Go to Dashboard
              </Link>
              <a
                href="/auth/logout"
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
              >
                Log out
              </a>
            </>
          ) : (
            <>
              <a
                href="/auth/login"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Log in
              </a>
              <a
                href="/auth/login?screen_hint=signup"
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
              >
                Sign up
              </a>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
