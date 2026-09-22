import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Without this guard, clerkMiddleware() throws on every single request
// (including the public landing/security/demo pages, which have nothing to
// do with auth) the moment Clerk keys aren't set — which is the state of a
// fresh checkout of this repo before someone creates a Clerk account.
const CLERK_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
);

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);

const withClerk = clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export default function middleware(req: NextRequest, event: unknown) {
  if (!CLERK_CONFIGURED) {
    return NextResponse.next();
  }
  // @ts-expect-error -- clerkMiddleware's inner handler expects Next's
  // internal NextFetchEvent, which isn't exported for us to type this with.
  return withClerk(req, event);
}

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
