"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { datasetApi } from "@/lib/api";
import { Search, Download, FileSpreadsheet, Loader2, Package } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { DatasetItem } from "@/types";

export default function DatasetPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [exporting, setExporting] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["dataset", page, search],
    queryFn: () => datasetApi.list({ page, page_size: 50, search: search || undefined }),
  });

  const handleExport = async (format: "csv" | "xlsx") => {
    setExporting(format);
    try {
      const res = format === "csv" ? await datasetApi.exportCsv() : await datasetApi.exportXlsx();
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bill_data.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed", e);
    } finally {
      setExporting(null);
    }
  };

  const items: DatasetItem[] = data?.data?.items || [];
  const total = data?.data?.total || 0;
  const totalPages = data?.data?.total_pages || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dataset</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">{total} items</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => handleExport("csv")} disabled={!!exporting} className="btn-outline flex items-center gap-2">
            {exporting === "csv" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            CSV
          </button>
          <button onClick={() => handleExport("xlsx")} disabled={!!exporting} className="btn-outline flex items-center gap-2">
            {exporting === "xlsx" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />}
            Excel
          </button>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input type="text" placeholder="Search products, batch IDs, sellers..." value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="input pl-10" />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Batch ID</th>
                    <th>Expiry</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>Amount</th>
                    <th>Seller</th>
                    <th>Bill No.</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr key={i}>
                      <td className="font-medium">{item["Product Name"] || "N/A"}</td>
                      <td>{item["Batch ID"] || "N/A"}</td>
                      <td>{item["Expiry Date"] || "N/A"}</td>
                      <td className="text-center">{item["Quantity"] ?? 0}</td>
                      <td>{formatCurrency(item["Unit Price"])}</td>
                      <td className="font-medium">{formatCurrency(item["Total Price"])}</td>
                      <td className="text-gray-600 dark:text-gray-300">{item["Seller Name"] || "N/A"}</td>
                      <td className="text-gray-600 dark:text-gray-300">{item["Bill Number"] || "N/A"}</td>
                      <td className="text-gray-600 dark:text-gray-300">{item["Bill Date"] || "N/A"}</td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center py-12">
                        <Package className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
                        <p className="text-gray-500 dark:text-gray-400">No items found.</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-outline disabled:opacity-50">Previous</button>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-outline disabled:opacity-50">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
