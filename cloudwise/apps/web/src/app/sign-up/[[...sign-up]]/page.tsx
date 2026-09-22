import { SignUp } from "@clerk/nextjs";
import { ClerkGate } from "@/components/clerk-gate";

export default function SignUpPage() {
  return (
    <ClerkGate>
      <div className="flex flex-1 items-center justify-center py-16">
        <SignUp />
      </div>
    </ClerkGate>
  );
}
