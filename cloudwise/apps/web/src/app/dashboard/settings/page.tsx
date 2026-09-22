"use client";

import { useEffect, useState } from "react";
import { useAuth, OrganizationProfile } from "@clerk/nextjs";
import { api, type Entitlement, ApiError } from "@/lib/api";

export default function SettingsPage() {
  const { getToken } = useAuth();
  const [entitlement, setEntitlement] = useState<Entitlement | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      setEntitlement(await api.getEntitlement(token));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function upgrade(tier: "starter" | "growth") {
    setCheckoutBusy(tier);
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      const { checkout_url } = await api.createCheckout(
        token,
        tier,
        `${window.location.origin}/dashboard/settings?upgraded=1`,
        `${window.location.origin}/dashboard/settings`
      );
      window.location.href = checkout_url;
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Couldn't start checkout: ${err.message}`
          : "Billing isn't configured yet on this deployment."
      );
    } finally {
      setCheckoutBusy(null);
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-xl font-semibold">Settings</h1>

      <section className="rounded-lg border border-border bg-surface p-4">
        <h2 className="text-sm font-medium">Plan</h2>
        {entitlement ? (
          <div className="mt-2 text-sm text-muted">
            <span className="capitalize text-foreground">{entitlement.tier}</span> ·{" "}
            {entitlement.max_accounts === null
              ? "unlimited accounts"
              : `up to ${entitlement.max_accounts} account(s)`}{" "}
            · {entitlement.status}
          </div>
        ) : (
          <div className="mt-2 text-sm text-muted">Loading…</div>
        )}
        {error && <div className="mt-2 text-sm text-danger">{error}</div>}
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => upgrade("starter")}
            disabled={checkoutBusy !== null}
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
          >
            {checkoutBusy === "starter" ? "Redirecting…" : "Upgrade to Starter"}
          </button>
          <button
            onClick={() => upgrade("growth")}
            disabled={checkoutBusy !== null}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-foreground disabled:opacity-50"
          >
            {checkoutBusy === "growth" ? "Redirecting…" : "Upgrade to Growth"}
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium">Team &amp; roles</h2>
        <p className="mb-3 text-sm text-muted">
          Managed through Clerk&apos;s organization membership — roles map to CloudWise&apos;s owner / admin /
          approver / viewer on first sign-in (see apps/api/app/provisioning.py).
        </p>
        <OrganizationProfile routing="hash" />
      </section>
    </div>
  );
}
