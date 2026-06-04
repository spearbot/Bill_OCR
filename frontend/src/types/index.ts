export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
}

export interface Bill {
  id: string;
  seller_name: string | null;
  gst_number: string | null;
  bill_number: string | null;
  bill_date: string | null;
  total_amount: number | null;
  upload_path: string;
  file_type: string;
  ocr_confidence: number | null;
  status: string;
  uploaded_by: string;
  processing_log: string | null;
  item_count?: number;
  items?: any[];
  created_at: string;
  updated_at: string;
}

export interface DatasetItem {
  "Seller Name"?: string;
  "GST Number"?: string;
  "Bill Number"?: string;
  "Bill Date"?: string;
  "Total Amount"?: number;
  "Product Name"?: string;
  "Batch ID"?: string;
  "Expiry Date"?: string;
  "Quantity"?: number;
  "Unit Price"?: number;
  "Total Price"?: number;
  "Upload Timestamp"?: string;
  "Status"?: string;
}

export interface DashboardStats {
  total_bills: number;
  total_items: number;
  total_users: number;
  pending_bills: number;
  processing_bills: number;
  completed_bills: number;
  failed_bills: number;
  review_bills: number;
  recent_bills: { id: string; seller_name: string | null; bill_number: string | null; status: string; created_at: string }[];
}
