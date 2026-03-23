"use client";

import { useUser, getAccessToken } from "@auth0/nextjs-auth0";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface AcceptResult {
  stakeholder_id: string;
  matter_id: string;
  matter_title: string;
  role: string;
}

/**
 * Invite acceptance flow:
 * 1. User lands on /invite/[token]
 * 2. If not authenticated, redirect to Auth0 login (proxy handles this)
 * 3. Once authenticated, call POST /api/v1/auth/accept-invite
 * 4. Redirect to the matter dashboard
 */
export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [status, setStatus] = useState<
    "loading" | "accepting" | "success" | "error"
  >("loading");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AcceptResult | null>(null);

  useEffect(() => {
    if (userLoading) return;

    if (!user) {
      // Not logged in — redirect to Auth0 login, then back here
      window.location.href = `/auth/login?returnTo=/invite/${token}`;
      return;
    }

    // User is authenticated — accept the invitation
    setStatus("accepting");

    (async () => {
      try {
        const accessToken = await getAccessToken();

        const response = await fetch(`${API_BASE_URL}/auth/accept-invite`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ invite_token: token }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to accept invitation");
        }

        const data: AcceptResult = await response.json();
        setResult(data);
        setStatus("success");

        // Redirect beneficiaries to the portal, others to the dashboard
        setTimeout(() => {
          if (data.role === "beneficiary" || data.role === "read_only") {
            router.push(`/portal/${data.matter_id}`);
          } else {
            router.push(`/matters/${data.matter_id}`);
          }
        }, 2000);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        setStatus("error");
      }
    })();
  }, [user, userLoading, token, router]);

  if (status === "loading" || status === "accepting") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin mb-4 mx-auto h-8 w-8 rounded-full border-4 border-gray-200 border-t-blue-600" />
          <p className="text-muted-foreground">
            {status === "loading"
              ? "Verifying your identity..."
              : "Accepting invitation..."}
          </p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center max-w-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">
            Unable to Accept Invitation
          </h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Go to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold text-green-600 mb-2">
          Invitation Accepted
        </h2>
        {result && (
          <p className="text-muted-foreground mb-4">
            You have been added to <strong>{result.matter_title}</strong> as a{" "}
            <strong>{result.role.replace("_", " ")}</strong>.
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          Redirecting to the matter...
        </p>
      </div>
    </div>
  );
}
