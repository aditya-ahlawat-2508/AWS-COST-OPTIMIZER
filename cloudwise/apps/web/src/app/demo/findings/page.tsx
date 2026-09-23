"use client";

import { useEffect, useState } from "react";
import { api, type Finding } from "@/lib/api";
import { FindingsTable } from "@/components/findings-table";

export default function DemoFindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    api.demoFindings().then(setFindings);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Recommendations</h1>
      <div className="overflow-hidden card">
        <FindingsTable findings={findings} />
      </div>
    </div>
  );
}
