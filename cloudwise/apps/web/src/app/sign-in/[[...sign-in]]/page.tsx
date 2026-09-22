import { SignIn } from "@clerk/nextjs";
import { ClerkGate } from "@/components/clerk-gate";

export default function SignInPage() {
  return (
    <ClerkGate>
      <div className="flex flex-1 items-center justify-center py-16">
        <SignIn />
      </div>
    </ClerkGate>
  );
}
