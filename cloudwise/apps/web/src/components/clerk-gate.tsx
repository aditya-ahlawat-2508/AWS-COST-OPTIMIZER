"use client";

import { ClerkProvider } from "@clerk/nextjs";

const CLERK_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

/**
 * Scopes Clerk to only the routes that need it (dashboard, sign-in, sign-up)
 * rather than the root layout — so the public marketing/security/demo pages
 * render fine even when Clerk hasn't been configured yet, instead of every
 * page in the app throwing because ClerkProvider has no publishableKey.
 * Also turns that throw into a readable message for local/preview
 * deployments that haven't set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY yet.
 */
export function ClerkGate({ children }: { children: React.ReactNode }) {
  if (!CLERK_CONFIGURED) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
        <h1 className="text-lg font-semibold">Clerk isn&apos;t configured on this deployment</h1>
        <p className="max-w-md text-sm text-muted">
          Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY (see .env.local.example) to
          use sign-in and the dashboard.
        </p>
      </div>
    );
  }

  return <ClerkProvider>{children}</ClerkProvider>;
}
