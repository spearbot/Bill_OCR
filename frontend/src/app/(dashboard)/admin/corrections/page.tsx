"use client";

import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Sparkles } from "lucide-react";

export default function CorrectionAnalyticsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (user?.role !== "admin") router.push("/dataset");
  }, [user, router]);

  if (user?.role !== "admin") return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary-500" />
          AI Learning Analytics
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Track how the system learns from user corrections</p>
      </div>
      <div className="card p-8 text-center text-gray-500">
        Correction tracking is disabled in the simplified architecture.
        All data is stored in Excel for simplicity.
      </div>
    </div>
  );
}
