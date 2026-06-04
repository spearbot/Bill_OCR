import os
import re
import json
import math
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DATA_DIR = Path(settings.DATA_DIR)
DATA_DIR.mkdir(exist_ok=True)

# Users file (simple JSON - no DB needed for a handful of users)
USERS_FILE = DATA_DIR / "users.json"
BILLS_META_FILE = DATA_DIR / "bills_meta.json"

EXCEL_FILE = DATA_DIR / "bill_data.xlsx"

COLUMNS = [
    "Bill ID", "Seller Name", "GST Number", "Bill Number",
    "Bill Date", "Total Amount", "Product Name", "Batch ID",
    "Expiry Date", "Quantity", "Unit Price", "Total Price",
    "Upload Timestamp", "Status",
]


def _init_users_file():
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def _init_meta_file():
    if not BILLS_META_FILE.exists():
        BILLS_META_FILE.write_text("[]", encoding="utf-8")


_init_users_file()
_init_meta_file()


# ─── User Storage (JSON) ────────────────────────────────────────

def load_users() -> List[Dict]:
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def save_users(users: List[Dict]):
    USERS_FILE.write_text(json.dumps(users, indent=2, default=str), encoding="utf-8")


def get_user_by_email(email: str) -> Optional[Dict]:
    for u in load_users():
        if u["email"] == email:
            return u
    return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    for u in load_users():
        if u["id"] == user_id:
            return u
    return None


def create_user(user: Dict):
    users = load_users()
    users.append(user)
    save_users(users)


def update_user(user_id: str, updates: Dict):
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u.update(updates)
            break
    save_users(users)


def delete_user(user_id: str):
    users = [u for u in load_users() if u["id"] != user_id]
    save_users(users)


# ─── Bill Meta Storage (JSON - for listing/searching) ──────────

def load_bills_meta() -> List[Dict]:
    return json.loads(BILLS_META_FILE.read_text(encoding="utf-8"))


def save_bills_meta(bills: List[Dict]):
    BILLS_META_FILE.write_text(json.dumps(bills, indent=2, default=str), encoding="utf-8")


def add_bill_meta(bill: Dict):
    bills = load_bills_meta()
    bills.insert(0, bill)
    save_bills_meta(bills)


def update_bill_meta(bill_id: str, updates: Dict):
    bills = load_bills_meta()
    for b in bills:
        if b["id"] == bill_id:
            b.update(updates)
            break
    save_bills_meta(bills)


def delete_bill_meta(bill_id: str):
    bills = [b for b in load_bills_meta() if b["id"] != bill_id]
    save_bills_meta(bills)


def get_bill_meta(bill_id: str) -> Optional[Dict]:
    for b in load_bills_meta():
        if b["id"] == bill_id:
            return b
    return None


def list_bills_meta(
    page: int = 1, page_size: int = 20,
    search: Optional[str] = None, status_filter: Optional[str] = None,
    seller_name: Optional[str] = None,
) -> Dict:
    bills = load_bills_meta()
    if search:
        s = search.lower()
        bills = [b for b in bills if s in (b.get("seller_name") or "").lower()
                 or s in (b.get("bill_number") or "").lower()
                 or s in (b.get("gst_number") or "").lower()]
    if status_filter:
        bills = [b for b in bills if b.get("status") == status_filter]
    if seller_name:
        bills = [b for b in bills if seller_name.lower() in (b.get("seller_name") or "").lower()]

    total = len(bills)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_bills = bills[offset:offset + page_size]
    return {"bills": page_bills, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


# ─── Excel Storage ──────────────────────────────────────────────

def _get_excel() -> Dict[str, pd.DataFrame]:
    if EXCEL_FILE.exists():
        try:
            return pd.read_excel(EXCEL_FILE, sheet_name=None)
        except Exception:
            return {}
    return {}


def _write_excel(sheets: Dict[str, pd.DataFrame]):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max((len(str(c.value or "")) for c in col), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 50)


def _get_month_sheet(date: datetime) -> str:
    return date.strftime("%Y-%m")


def save_bill_to_excel(bill_data: Dict, items: List[Dict]):
    sheets = _get_excel()
    bill_id = bill_data.get("id", "")
    bill_date = bill_data.get("bill_date") or datetime.now()
    if isinstance(bill_date, str):
        try:
            bill_date = datetime.fromisoformat(bill_date)
        except ValueError:
            bill_date = datetime.now()
    sheet_name = _get_month_sheet(bill_date)

    logger.info(f"save_bill_to_excel: bill_id={bill_id!r} items_count={len(items)} sheet={sheet_name!r}")

    rows = []
    seller = bill_data.get("seller_name", "")
    for item in items:
        rows.append({
            "Bill ID": bill_id,
            "Seller Name": seller,
            "GST Number": bill_data.get("gst_number", ""),
            "Bill Number": bill_data.get("bill_number", ""),
            "Bill Date": bill_date.strftime("%Y-%m-%d") if hasattr(bill_date, "strftime") else str(bill_date),
            "Total Amount": bill_data.get("total_amount"),
            "Product Name": item.get("product_name", ""),
            "Batch ID": item.get("batch_id", ""),
            "Expiry Date": item.get("expiry_date", ""),
            "Quantity": item.get("quantity"),
            "Unit Price": item.get("unit_price"),
            "Total Price": item.get("total_price"),
            "Upload Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": bill_data.get("status", "review"),
        })

    new_df = pd.DataFrame(rows)
    logger.info(f"  DataFrame columns: {list(new_df.columns)}")
    logger.info(f"  DataFrame shape: {new_df.shape}")
    if sheet_name in sheets:
        df = sheets[sheet_name]
        logger.info(f"  Existing sheet '{sheet_name}' has {len(df)} rows before append")
        df = pd.concat([df, new_df], ignore_index=True)
        # Sort by seller name to keep groups together
        df = df.sort_values(["Seller Name", "Bill Date", "Product Name"]).reset_index(drop=True)
        sheets[sheet_name] = df
    else:
        logger.info(f"  Creating new sheet '{sheet_name}'")
        sheets[sheet_name] = new_df

    _write_excel(sheets)
    logger.info(f"Saved {len(rows)} rows to Excel sheet '{sheet_name}'")


def update_bill_in_excel(bill_id: str, bill_data: Dict, items: List[Dict]):
    """Rewrite the rows for this bill. Since Excel is append-only by design,
    we remove old rows for this bill and append new ones."""
    sheets = _get_excel()
    bill_date = bill_data.get("bill_date") or datetime.now()
    if isinstance(bill_date, str):
        try:
            bill_date = datetime.fromisoformat(bill_date)
        except ValueError:
            bill_date = datetime.now()
    sheet_name = _get_month_sheet(bill_date)

    if sheet_name not in sheets:
        save_bill_to_excel(bill_data, items)
        return

    df = sheets[sheet_name]
    if "Bill ID" in df.columns:
        df = df[df["Bill ID"] != bill_id]

    rows = []
    seller = bill_data.get("seller_name", "")
    for item in items:
        rows.append({
            "Bill ID": bill_id,
            "Seller Name": seller,
            "GST Number": bill_data.get("gst_number", ""),
            "Bill Number": bill_data.get("bill_number", ""),
            "Bill Date": bill_date.strftime("%Y-%m-%d") if hasattr(bill_date, "strftime") else str(bill_date),
            "Total Amount": bill_data.get("total_amount"),
            "Product Name": item.get("product_name", ""),
            "Batch ID": item.get("batch_id", ""),
            "Expiry Date": item.get("expiry_date", ""),
            "Quantity": item.get("quantity"),
            "Unit Price": item.get("unit_price"),
            "Total Price": item.get("total_price"),
            "Upload Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": bill_data.get("status", "completed"),
        })

    new_df = pd.DataFrame(rows)
    df = pd.concat([df, new_df], ignore_index=True)
    df = df.sort_values(["Seller Name", "Bill Date", "Product Name"]).reset_index(drop=True)
    sheets[sheet_name] = df
    _write_excel(sheets)


def delete_bill_from_excel(bill_id: str):
    sheets = _get_excel()
    modified = False
    for sheet_name in list(sheets.keys()):
        df = sheets[sheet_name]
        if "Bill ID" in df.columns:
            before = len(df)
            df = df[df["Bill ID"] != bill_id]
            if len(df) < before:
                sheets[sheet_name] = df
                modified = True
    if modified:
        _write_excel(sheets)


def _clean_nan(records: List[Dict]) -> List[Dict]:
    for r in records:
        for k, v in r.items():
            if isinstance(v, float) and math.isnan(v):
                r[k] = None
    return records

def get_dataset_items(search: Optional[str] = None) -> List[Dict]:
    sheets = _get_excel()
    all_rows = []
    for sheet_name, df in sheets.items():
        records = _clean_nan(df.to_dict(orient="records"))
        for r in records:
            r["_sheet"] = sheet_name
        all_rows.extend(records)

    logger.info(f"get_dataset_items: loaded {len(all_rows)} rows from {len(sheets)} sheets")
    if all_rows and len(all_rows) > 0:
        logger.info(f"  First row keys: {list(all_rows[0].keys())}")
        logger.info(f"  Bill ID in first row: {all_rows[0].get('Bill ID', 'MISSING')!r}")

    if search:
        s = search.lower()
        all_rows = [r for r in all_rows if
                    s in str(r.get("Product Name", "")).lower()
                    or s in str(r.get("Batch ID", "")).lower()
                    or s in str(r.get("Seller Name", "")).lower()]

    all_rows.sort(key=lambda r: r.get("Upload Timestamp", ""), reverse=True)
    return all_rows


# ─── Google Sheets (optional) ──────────────────────────────────

def _get_gs_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("gspread not installed. Install: pip install gspread google-auth")
        return None

    if not settings.GOOGLE_SHEETS_ENABLED or not settings.GOOGLE_SHEET_ID:
        return None

    try:
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        return gc.open_by_key(settings.GOOGLE_SHEET_ID)
    except Exception as e:
        logger.error(f"Google Sheets auth failed: {e}")
        return None


def save_to_google_sheets(bill_data: Dict, items: List[Dict]):
    client = _get_gs_client()
    if not client:
        return

    bill_date = bill_data.get("bill_date") or datetime.now()
    if isinstance(bill_date, str):
        try:
            bill_date = datetime.fromisoformat(bill_date)
        except ValueError:
            bill_date = datetime.now()
    sheet_name = _get_month_sheet(bill_date)

    try:
        ws = client.worksheet(sheet_name)
    except Exception:
        ws = client.add_worksheet(title=sheet_name, rows=1000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)

    bill_id = bill_data.get("id", "")
    seller = bill_data.get("seller_name", "")
    for item in items:
        ws.append_row([
            bill_id,
            seller,
            bill_data.get("gst_number", ""),
            bill_data.get("bill_number", ""),
            bill_date.strftime("%Y-%m-%d") if hasattr(bill_date, "strftime") else str(bill_date),
            bill_data.get("total_amount"),
            item.get("product_name", ""),
            item.get("batch_id", ""),
            item.get("expiry_date", ""),
            item.get("quantity"),
            item.get("unit_price"),
            item.get("total_price"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            bill_data.get("status", "review"),
        ])
    logger.info(f"Saved {len(items)} rows to Google Sheets '{sheet_name}'")


def save_data(bill_data: Dict, items: List[Dict]):
    mode = settings.STORAGE_MODE
    if mode in ("excel", "both"):
        save_bill_to_excel(bill_data, items)
    if mode in ("google_sheets", "both"):
        save_to_google_sheets(bill_data, items)


# ─── Stats ──────────────────────────────────────────────────────

def normalize_seller(name: Optional[str]) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_verified_gst_for_seller(seller_name: Optional[str]) -> Optional[str]:
    """Look up the most commonly occurring GST for a seller in existing data."""
    normalized = normalize_seller(seller_name)
    if not normalized:
        return None
    sheets = _get_excel()
    gst_counts: Dict[str, int] = {}
    for df in sheets.values():
        df = df.where(pd.notna(df), None)
        records = df.to_dict(orient="records")
        for r in records:
            existing_seller = normalize_seller(r.get("Seller Name"))
            existing_gst = r.get("GST Number")
            if existing_seller and existing_gst and isinstance(existing_gst, str) and len(existing_gst) > 5:
                if existing_seller == normalized or existing_seller in normalized or normalized in existing_seller:
                    gst_counts[existing_gst] = gst_counts.get(existing_gst, 0) + 1
    # Also check bills_meta
    bills = load_bills_meta()
    for b in bills:
        s = normalize_seller(b.get("seller_name"))
        g = b.get("gst_number")
        if s and g and isinstance(g, str) and len(g) > 5:
            if s == normalized or s in normalized or normalized in s:
                gst_counts[g] = gst_counts.get(g, 0) + 1
    if gst_counts:
        return max(gst_counts, key=gst_counts.get)
    return None


def get_stats() -> Dict:
    bills = load_bills_meta()
    total_bills = len(bills)
    total_items = 0
    status_counts = {}
    for b in bills:
        s = b.get("status", "pending")
        status_counts[s] = status_counts.get(s, 0) + 1
        total_items += b.get("item_count", 0)

    recent = sorted(bills, key=lambda x: x.get("created_at", ""), reverse=True)[:10]

    return {
        "total_bills": total_bills,
        "total_items": total_items,
        "total_users": len(load_users()),
        **{f"{k}_bills": v for k, v in status_counts.items()},
        "pending_bills": status_counts.get("pending", 0),
        "processing_bills": status_counts.get("processing", 0),
        "completed_bills": status_counts.get("completed", 0),
        "failed_bills": status_counts.get("failed", 0),
        "review_bills": status_counts.get("review", 0),
        "recent_bills": [
            {"id": b["id"], "seller_name": b.get("seller_name"),
             "bill_number": b.get("bill_number"), "status": b.get("status"),
             "created_at": b.get("created_at")}
            for b in recent
        ],
    }
