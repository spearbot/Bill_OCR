"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { billsApi } from "@/lib/api";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
  Search,
  Filter,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { formatDate, formatCurrency, getStatusColor } from "@/lib/utils";
import { Bill } from "@/types";

export default function BillsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["bills", page, search, statusFilter],
    queryFn: () =>
      billsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status_filter: statusFilter || undefined,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => billsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      toast.success("Bill deleted");
    },
    onError: () => {
      toast.error("Failed to delete bill");
    },
  });

  const bills = data?.data?.bills || [];
  const totalPages = data?.data?.total_pages || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bills</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage your uploaded bills
          </p>
        </div>
      </div>

      <div className="card p-4">
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by seller, bill number, GST..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="input pl-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="input sm:w-48"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="review">Review</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Seller</th>
                    <th>Bill No.</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Items</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {bills.map((bill: Bill) => (
                    <tr key={bill.id}>
                      <td className="font-medium text-gray-900 dark:text-white">
                        {bill.seller_name || "N/A"}
                      </td>
                      <td className="text-gray-600 dark:text-gray-300">
                        {bill.bill_number || "N/A"}
                      </td>
                      <td className="text-gray-600 dark:text-gray-300">
                        {formatDate(bill.bill_date)}
                      </td>
                      <td className="text-gray-600 dark:text-gray-300">
                        {formatCurrency(bill.total_amount)}
                      </td>
                      <td className="text-gray-600 dark:text-gray-300">
                        {bill.item_count ?? 0}
                      </td>
                      <td>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                            bill.status
                          )}`}
                        >
                          {bill.status}
                        </span>
                      </td>
                      <td className="text-gray-600 dark:text-gray-300">
                        {formatDate(bill.created_at)}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => router.push(`/review/${bill.id}`)}
                            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            title="View/Edit"
                          >
                            <Eye className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                          </button>
                          <button
                            onClick={() => deleteMutation.mutate(bill.id)}
                            className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {bills.length === 0 && (
                    <tr>
                      <td colSpan={8} className="text-center py-12 text-gray-500 dark:text-gray-400">
                        No bills found. Upload your first bill to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="btn-outline disabled:opacity-50"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="btn-outline disabled:opacity-50"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
