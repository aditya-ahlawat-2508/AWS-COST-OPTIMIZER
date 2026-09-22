"use client";

import { OrganizationSwitcher, UserButton, useOrganization } from "@clerk/nextjs";
import { ClerkGate } from "@/components/clerk-gate";
import { Sidebar } from "@/components/sidebar";

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { organization, isLoaded } = useOrganization();

  if (isLoaded && !organization) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
        <h1 className="text-xl font-semibold">Create or select an organization</h1>
        <p className="max-w-md text-sm text-muted">
          CloudWise scopes every AWS account, finding, and audit entry to a Clerk organization —
          create one to continue. This is what becomes your CloudWise org.
        </p>
        <OrganizationSwitcher hidePersonal afterCreateOrganizationUrl="/dashboard" afterSelectOrganizationUrl="/dashboard" />
      </div>
    );
  }

  return (
    <div className="flex flex-1">
      <Sidebar
        orgLabel={organization?.name}
        footer={
          <div className="flex items-center justify-between">
            <OrganizationSwitcher afterSelectOrganizationUrl="/dashboard" />
            <UserButton />
          </div>
        }
      />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkGate>
      <DashboardShell>{children}</DashboardShell>
    </ClerkGate>
  );
}
