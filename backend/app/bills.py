import os
import uuid
import time
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image, ImageOps
import pandas as pd
import io

from app.security import get_current_user
from app.store import (
    add_bill_meta, get_bill_meta, update_bill_meta, delete_bill_meta,
    list_bills_meta, get_dataset_items, save_data, delete_bill_from_excel,
    update_bill_in_excel, get_verified_gst_for_seller, normalize_seller,
    load_bills_meta,
)
from app.ocr_service import OCRService
from app.field_extractor import FieldExtractor
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/bills", tags=["Bills"])

ocr_service = OCRService()
extractor = FieldExtractor()


class ItemData(BaseModel):
    product_name: Optional[str] = None
    batch_id: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class BillUpdate(BaseModel):
    seller_name: Optional[str] = None
    gst_number: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None
    items: Optional[List[ItemData]] = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_bill(file: UploadFile = File(...), payload: dict = Depends(get_current_user)):
    start = time.time()
    bill_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {ext}")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, f"{bill_id}_{file.filename}")
    with open(path, "wb") as f:
        f.write(content)

    # Correct EXIF orientation so images display right-side-up and OCR gets correct orientation
    if ext != "pdf":
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            if img:
                img.save(path)
        except Exception:
            pass

    meta = {
        "id": bill_id, "upload_path": path, "file_type": ext,
        "status": "processing", "uploaded_by": payload.get("user_id", ""),
        "seller_name": None, "gst_number": None, "bill_number": None,
        "bill_date": None, "total_amount": None, "ocr_confidence": None,
        "item_count": 0, "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    add_bill_meta(meta)

    try:
        if ext == "pdf":
            ocr_lines, confidence = ocr_service.extract_text_from_pdf(content)
        else:
            image = Image.open(path)
            ocr_lines, confidence = ocr_service.extract_text(image)

        logger.info(f"OCR: {len(ocr_lines)} lines, {confidence:.2%}")
        meta["ocr_confidence"] = confidence

        result = extractor.extract_all(ocr_lines)
        bill_level = result["bill_level"]
        items_data = result["items"]

        meta["seller_name"] = bill_level.get("seller_name")
        extracted_gst = bill_level.get("gst_number")
        verified_gst = get_verified_gst_for_seller(meta["seller_name"]) if meta["seller_name"] else None
        if verified_gst and extracted_gst and extracted_gst != verified_gst:
            logger.warning(f"GST mismatch for '{meta['seller_name']}': OCR={extracted_gst}, stored={verified_gst}. Keeping stored GST.")
            meta["gst_number"] = verified_gst
            meta["_gst_discrepancy"] = f"OCR detected {extracted_gst}, kept verified {verified_gst}"
        else:
            meta["gst_number"] = extracted_gst
        meta["bill_number"] = bill_level.get("bill_number")
        bill_date = bill_level.get("bill_date")
        meta["bill_date"] = bill_date.isoformat() if bill_date else None
        meta["total_amount"] = bill_level.get("total_amount")
        meta["item_count"] = len(items_data)
        meta["status"] = "review"
        meta["updated_at"] = datetime.now().isoformat()

        items = []
        for item_data in items_data:
            expiry_raw = item_data.get("expiry_date")
            items.append({
                "product_name": item_data.get("product_name"),
                "batch_id": item_data.get("batch_id"),
                "expiry_date": expiry_raw,
                "quantity": item_data.get("quantity"),
                "unit_price": item_data.get("unit_price"),
                "total_price": item_data.get("total_price"),
            })

        save_data(meta, items)
        update_bill_meta(bill_id, meta)

        elapsed = (time.time() - start) * 1000
        logger.info(f"Upload complete: {bill_id}, {len(items_data)} items, {elapsed:.0f}ms")

        return {**meta, "items": items, "processing_time_ms": elapsed}

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        meta["status"] = "failed"
        meta["updated_at"] = datetime.now().isoformat()
        update_bill_meta(bill_id, meta)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/retry")
async def retry_bills(bill_id: Optional[str] = None, payload: dict = Depends(get_current_user)):
    start = time.time()
    all_bills = load_bills_meta()
    failed = [b for b in all_bills if b.get("status") == "failed"]
    if bill_id:
        failed = [b for b in failed if b["id"] == bill_id]
        if not failed:
            raise HTTPException(status_code=404, detail="No failed bill found with that ID")

    results = []
    for bill in failed:
        bid = bill["id"]
        path = bill.get("upload_path", "")
        ext = bill.get("file_type", "jpg")
        logger.info(f"Retrying bill {bid} ({path})")

        if not os.path.exists(path):
            logger.warning(f"Skip {bid}: image not found at {path}")
            results.append({"id": bid, "status": "skipped", "reason": "image_not_found"})
            continue

        meta = dict(bill)
        meta["status"] = "processing"
        meta["updated_at"] = datetime.now().isoformat()
        update_bill_meta(bid, meta)

        try:
            image = Image.open(path)
            ocr_lines, confidence = ocr_service.extract_text(image)
            meta["ocr_confidence"] = confidence

            result = extractor.extract_all(ocr_lines)
            bill_level = result["bill_level"]
            items_data = result["items"]

            meta["seller_name"] = bill_level.get("seller_name")
            meta["gst_number"] = bill_level.get("gst_number")
            meta["bill_number"] = bill_level.get("bill_number")
            bd = bill_level.get("bill_date")
            meta["bill_date"] = bd.isoformat() if bd else None
            meta["total_amount"] = bill_level.get("total_amount")
            meta["item_count"] = len(items_data)
            meta["status"] = "review"
            meta["updated_at"] = datetime.now().isoformat()

            items = [{
                "product_name": it.get("product_name"),
                "batch_id": it.get("batch_id"),
                "expiry_date": it.get("expiry_date"),
                "quantity": it.get("quantity"),
                "unit_price": it.get("unit_price"),
                "total_price": it.get("total_price"),
            } for it in items_data]

            save_data(meta, items)
            update_bill_meta(bid, meta)
            logger.info(f"Retry success: {bid}, {len(items)} items")
            results.append({"id": bid, "status": "success", "item_count": len(items)})
        except Exception as e:
            logger.error(f"Retry failed for {bid}: {e}", exc_info=True)
            meta["status"] = "failed"
            meta["updated_at"] = datetime.now().isoformat()
            update_bill_meta(bid, meta)
            results.append({"id": bid, "status": "failed", "error": str(e)})

    elapsed = (time.time() - start) * 1000
    return {"results": results, "total": len(results), "processing_time_ms": elapsed}


@router.get("/")
async def list_bills(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, status_filter: Optional[str] = None,
    seller_name: Optional[str] = None,
    payload: dict = Depends(get_current_user),
):
    return list_bills_meta(page=page, page_size=page_size, search=search,
                           status_filter=status_filter, seller_name=seller_name)


# ─── Dataset & Export (must be before /{bill_id} routes) ──────

@router.get("/dataset/items")
async def dataset_items(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    payload: dict = Depends(get_current_user),
):
    all_items = get_dataset_items(search=search)
    total = len(all_items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_items = all_items[offset:offset + page_size]
    return {
        "items": page_items, "total": total, "page": page,
        "page_size": page_size, "total_pages": total_pages,
    }


@router.get("/export/csv")
async def export_csv(
    search: Optional[str] = None,
    payload: dict = Depends(get_current_user),
):
    items = get_dataset_items(search=search)
    df = pd.DataFrame(items)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bill_data.csv"},
    )


@router.get("/export/xlsx")
async def export_xlsx(
    search: Optional[str] = None,
    payload: dict = Depends(get_current_user),
):
    items = get_dataset_items(search=search)
    df = pd.DataFrame(items)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Exported Data")
    output.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=bill_data.xlsx"},
    )


@router.get("/{bill_id}")
async def get_bill(bill_id: str, payload: dict = Depends(get_current_user)):
    bill = get_bill_meta(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.put("/{bill_id}")
async def update_bill(bill_id: str, data: BillUpdate, payload: dict = Depends(get_current_user)):
    bill = get_bill_meta(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    updates = data.model_dump(exclude_unset=True)
    items_data = updates.pop("items", None)
    updates["status"] = "completed"
    updates["updated_at"] = datetime.now().isoformat()
    if items_data is not None and len(items_data) > 0:
        updates["item_count"] = len(items_data)
    update_bill_meta(bill_id, updates)

    # Also update Excel
    updated = get_bill_meta(bill_id)
    if updated:
        if items_data is not None and len(items_data) > 0:
            saved_items = []
            for item_data in items_data:
                saved_items.append({
                    "product_name": item_data.product_name if isinstance(item_data, ItemData) else item_data.get("product_name"),
                    "batch_id": item_data.batch_id if isinstance(item_data, ItemData) else item_data.get("batch_id"),
                    "expiry_date": item_data.expiry_date if isinstance(item_data, ItemData) else item_data.get("expiry_date"),
                    "quantity": item_data.quantity if isinstance(item_data, ItemData) else item_data.get("quantity"),
                    "unit_price": item_data.unit_price if isinstance(item_data, ItemData) else item_data.get("unit_price"),
                    "total_price": item_data.total_price if isinstance(item_data, ItemData) else item_data.get("total_price"),
                })
            update_bill_in_excel(bill_id, updated, saved_items)

    return get_bill_meta(bill_id)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill(bill_id: str, payload: dict = Depends(get_current_user)):
    bill = get_bill_meta(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if os.path.exists(bill.get("upload_path", "")):
        os.remove(bill["upload_path"])
    delete_bill_from_excel(bill_id)
    delete_bill_meta(bill_id)


@router.get("/{bill_id}/image")
async def get_bill_image(bill_id: str, payload: dict = Depends(get_current_user)):
    bill = get_bill_meta(bill_id)
    if not bill or not os.path.exists(bill.get("upload_path", "")):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(bill["upload_path"])


@router.get("/{bill_id}/items")
async def get_bill_items(bill_id: str, payload: dict = Depends(get_current_user)):
    bill = get_bill_meta(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    items = get_dataset_items()
    bill_items = [i for i in items if i.get("Bill ID") == bill_id]
    return bill_items
