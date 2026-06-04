"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  FileText,
  Package,
  Users,
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  XCircle,
  Eye,
} from "lucide-react";
import { DashboardStats } from "@/types";
import { formatDate } from "@/lib/utils";

export default function AdminPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    if (user?.role !== "admin") {
      router.push("/dataset");
    }
  }, [user, router]);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.stats(),
    enabled: user?.role === "admin",
  });

  const stats = data?.data as DashboardStats | undefined;

  if (user?.role !== "admin") {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          System overview and dataset management
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Bills"
          value={stats?.total_bills || 0}
          icon={FileText}
          color="blue"
        />
        <StatCard
          title="Total Items"
          value={stats?.total_items || 0}
          icon={Package}
          color="green"
        />
        <StatCard
          title="Total Users"
          value={stats?.total_users || 0}
          icon={Users}
          color="purple"
        />
        <StatCard
          title="Needs Review"
          value={stats?.review_bills || 0}
          icon={AlertTriangle}
          color="yellow"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Processing Status
          </h3>
          <div className="space-y-3">
            <StatusRow label="Completed" value={stats?.completed_bills || 0} color="green" />
            <StatusRow label="Pending Review" value={stats?.review_bills || 0} color="purple" />
            <StatusRow label="Processing" value={stats?.processing_bills || 0} color="blue" />
            <StatusRow label="Pending" value={stats?.pending_bills || 0} color="yellow" />
            <StatusRow label="Failed" value={stats?.failed_bills || 0} color="red" />
          </div>
        </div>

        <div className="card p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Recent Bills
          </h3>
          <div className="space-y-3">
            {stats?.recent_bills?.map((bill) => (
              <div
                key={bill.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {bill.seller_name || "Unknown Seller"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {bill.bill_number || "No bill number"} - {formatDate(bill.created_at)}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    bill.status === "completed"
                      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                      : bill.status === "failed"
                      ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      : bill.status === "review"
                      ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
                      : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                  }`}
                >
                  {bill.status}
                </span>
              </div>
            ))}
            {(!stats?.recent_bills || stats.recent_bills.length === 0) && (
              <p className="text-center py-8 text-gray-500 dark:text-gray-400">
                No bills uploaded yet
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: any;
  color: string;
}) {
  const colors: Record<string, string> = {
    blue: "bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400",
    green: "bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400",
    purple: "bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-400",
    yellow: "bg-yellow-100 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-400",
  };

  return (
    <div className="card p-4">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    green: "bg-green-500",
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${colors[color]}`} />
        <span className="text-sm text-gray-600 dark:text-gray-300">{label}</span>
      </div>
      <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>
    </div>
  );
}
