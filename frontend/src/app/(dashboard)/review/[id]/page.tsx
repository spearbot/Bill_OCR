"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, billsApi, datasetApi } from "@/lib/api";
import { toast } from "sonner";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Save, Trash2, Plus, Loader2, ImageIcon, CheckCircle } from "lucide-react";
import { formatDate, getStatusColor } from "@/lib/utils";

export default function ReviewPage() {
  const router = useRouter();
  const params = useParams();
  const billId = params.id as string;
  const queryClient = useQueryClient();

  const [billData, setBillData] = useState<any>({});
  const [items, setItems] = useState<any[]>([]);
  const [imageUrl, setImageUrl] = useState("");

  const { data: billRes, isLoading } = useQuery({
    queryKey: ["bill", billId],
    queryFn: () => billsApi.get(billId),
    enabled: !!billId,
  });

  const { data: itemsRes } = useQuery({
    queryKey: ["bill-items", billId],
    queryFn: () => billsApi.getItems(billId),
    enabled: !!billId,
  });

  useEffect(() => {
    if (billRes?.data) {
      const b = billRes.data;
      setBillData({
        seller_name: b.seller_name || "",
        gst_number: b.gst_number || "",
        bill_number: b.bill_number || "",
        bill_date: b.bill_date ? b.bill_date.slice(0, 10) : "",
        total_amount: b.total_amount || 0,
      });
    }
  }, [billRes]);

  useEffect(() => {
    if (itemsRes?.data && Array.isArray(itemsRes.data) && itemsRes.data.length > 0) {
      setItems(itemsRes.data.map((it: any) => ({
        product_name: it["Product Name"] || it.product_name || "",
        batch_id: it["Batch ID"] || it.batch_id || "",
        expiry_date: it["Expiry Date"] || it.expiry_date || "",
        quantity: it["Quantity"] ?? it.quantity ?? 0,
        unit_price: it["Unit Price"] ?? it.unit_price ?? 0,
        total_price: it["Total Price"] ?? it.total_price ?? 0,
      })));
    } else if (billRes?.data?.items && Array.isArray(billRes.data.items) && billRes.data.items.length > 0) {
      setItems(billRes.data.items.map((it: any) => ({
        product_name: it.product_name || "",
        batch_id: it.batch_id || "",
        expiry_date: it.expiry_date || "",
        quantity: it.quantity ?? 0,
        unit_price: it.unit_price ?? 0,
        total_price: it.total_price ?? 0,
      })));
    } else if (billRes?.data?.item_count && billRes.data.item_count > 0) {
      const count = billRes.data.item_count;
      setItems((prev) =>
        prev.length === 0 ? Array.from({ length: count }, () => ({
          product_name: "", batch_id: "", expiry_date: "", quantity: 0, unit_price: 0, total_price: 0,
        })) : prev
      );
    }
  }, [itemsRes, billRes]);

  useEffect(() => {
    let objectUrl: string | null = null;
    const loadImage = async () => {
      try {
        const response = await api.get(`/api/bills/${billId}/image`, {
          responseType: "blob",
        });
        objectUrl = URL.createObjectURL(response.data);
        setImageUrl(objectUrl);
      } catch {
        setImageUrl("");
      }
    };
    loadImage();
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [billId]);

  const updateMutation = useMutation({
    mutationFn: () => billsApi.update(billId, { ...billData, items }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["dataset"] });
      toast.success("Bill saved");
      router.push("/bills");
    },
    onError: () => toast.error("Failed to save"),
  });

  const addItem = () => setItems([...items, {
    product_name: "", batch_id: "", expiry_date: "", quantity: 0, unit_price: 0, total_price: 0,
  }]);
  const removeItem = (i: number) => setItems(items.filter((_, j) => j !== i));
  const updateItem = (i: number, field: string, value: any) => {
    const newItems = [...items];
    newItems[i] = { ...newItems[i], [field]: value };
    if (field === "quantity" || field === "unit_price") {
      const qty = field === "quantity" ? value : newItems[i].quantity || 0;
      const price = field === "unit_price" ? value : newItems[i].unit_price || 0;
      newItems[i].total_price = qty * price;
    }
    setItems(newItems);
  };

  if (isLoading) {
    return <div className="flex justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Review & Edit</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Verify and correct extracted data</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="card p-4 sticky top-20">
            <h3 className="text-lg font-medium mb-4">Bill Image</h3>
            <div className="aspect-[3/4] bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center">
              {imageUrl ? (
                <img src={imageUrl} alt="Bill" className="w-full h-full object-contain"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              ) : <ImageIcon className="h-12 w-12 text-gray-400" />}
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Status</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(billRes?.data?.status || "")}`}>
                  {billRes?.data?.status}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">OCR Confidence</span>
                <span className="font-medium">
                  {billRes?.data?.ocr_confidence ? `${(billRes.data.ocr_confidence * 100).toFixed(1)}%` : "N/A"}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card p-4">
            <h3 className="text-lg font-medium mb-4">Bill Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Seller Name</label>
                <input type="text" value={billData.seller_name || ""}
                  onChange={(e) => setBillData({ ...billData, seller_name: e.target.value })} className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Bill Number</label>
                <input type="text" value={billData.bill_number || ""}
                  onChange={(e) => setBillData({ ...billData, bill_number: e.target.value })} className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Bill Date</label>
                <input type="date" value={billData.bill_date || ""}
                  onChange={(e) => setBillData({ ...billData, bill_date: e.target.value })} className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">GST Number</label>
                <input type="text" value={billData.gst_number || ""}
                  onChange={(e) => setBillData({ ...billData, gst_number: e.target.value })} className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Total Amount</label>
                <input type="number" step="0.01" value={billData.total_amount || ""}
                  onChange={(e) => setBillData({ ...billData, total_amount: parseFloat(e.target.value) || 0 })} className="input" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">Items ({items.length})</h3>
              <button onClick={addItem} className="btn-outline flex items-center gap-2">
                <Plus className="h-4 w-4" /> Add Item
              </button>
            </div>
            <div className="space-y-4">
              {items.map((item, i) => (
                <div key={i} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-500">Item {i + 1}</span>
                    <button onClick={() => removeItem(i)} className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">Product Name</label>
                      <input type="text" value={item.product_name} onChange={(e) => updateItem(i, "product_name", e.target.value)} className="input" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Batch ID</label>
                      <input type="text" value={item.batch_id} onChange={(e) => updateItem(i, "batch_id", e.target.value)} className="input" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Expiry Date</label>
                      <input type="text" value={item.expiry_date} onChange={(e) => updateItem(i, "expiry_date", e.target.value)} className="input" placeholder="MM/YY" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Quantity</label>
                      <input type="number" value={item.quantity} onChange={(e) => updateItem(i, "quantity", parseInt(e.target.value) || 0)} className="input" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Unit Price</label>
                      <input type="number" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", parseFloat(e.target.value) || 0)} className="input" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Total Price</label>
                      <input type="number" step="0.01" value={item.total_price} onChange={(e) => updateItem(i, "total_price", parseFloat(e.target.value) || 0)} className="input" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button onClick={() => router.back()} className="btn-outline">Cancel</button>
            <button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending} className="btn-primary flex items-center gap-2">
              {updateMutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</>
                : <><CheckCircle className="h-4 w-4" /> Confirm & Save</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
