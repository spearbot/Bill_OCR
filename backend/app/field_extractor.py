import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class FieldExtractor:
    SELLER_KEYWORDS = [
        "pharmacy", "medical", "chemist", "hospital", "clinic",
        "mart", "enterprises", "distributors", "wholesale", "retail",
        "agencies", "drug", "wellness", "store",
    ]
    BILL_KEYWORDS = ["bill no", "invoice no", "bill number", "invoice number", "bill #", "inv no"]
    DATE_KEYWORDS = ["date", "bill date", "invoice date", "dated"]
    NET_TOTAL_KEYWORDS = [
        "net amount", "net amt", "amount payable", "net payable",
        "grand total", "total amount", "total",
    ]
    GST_PATTERN = r"\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]"
    MEDICINE_SUFFIXES = r"(TAB|CAP|SYR|INJ|CREAM|OINT|GEL|DROP|SYP|TABLET|MG|ML|GM)\b"

    COLUMN_DEFS = [
        ("product", ["description", "particulars", "item name", "product name", "medicine", "drug", "item", "product", "particular"]),
        ("batch", ["batch", "b.no", "bno", "b. no", "lot", "lot no", "lot no.", "bat no"]),
        ("expiry", ["exp", "expiry", "expire", "exp date", "use before", "best before", "exp dt"]),
        ("quantity", ["qty", "quantity", "nos", "qty.", "pack", "pcs"]),
        ("rate", ["rate", "unit price", "mrp", "ptr", "price", "unit rate"]),
        ("amount", ["amount", "amt", "value", "total price", "total", "net amount"]),
    ]

    BATCH_KEYWORDS = ["batch", "b.no", "bno", "lot", "lot no"]
    EXCLUDE_WORDS = {
        "batch", "exp", "qty", "rate", "amount", "mrp", "total", "net", "hsn",
        "gst", "cgst", "sgst", "description", "particulars", "s.no", "sr.no",
        "store", "cash", "mob", "date", "round", "disc", "tax", "pack", "code",
        "for:", "less", "ret", "cr", "note", "add", "please", "see", "backside",
        "rupees", "only", "thousand", "hundred", "twelve",
        "bill", "invoice", "inv", "item",
    }
    MONTH_MAP = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    DATE_PATTERNS = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
    ]

    def __init__(self):
        self.ocr_lines = []
        self.full_text = ""
        self.lines_by_position = []

    def extract_all(self, ocr_lines: List[Dict]) -> Dict:
        self.ocr_lines = ocr_lines
        self.full_text = "\n".join(l.get("text", "") for l in ocr_lines)
        self.lines_by_position = sorted(
            ocr_lines, key=lambda x: (x.get("bbox", [[0, 0]])[0][1], x.get("bbox", [[0, 0]])[0][0])
        )
        bill_level = self._extract_bill_level()
        items = self._extract_items()
        return {"bill_level": bill_level, "items": items}

    def _extract_bill_level(self) -> Dict:
        date_val = self._extract_bill_date()
        return {
            "seller_name": self._extract_seller_name(),
            "gst_number": self._extract_gst(),
            "bill_number": self._extract_bill_number(),
            "bill_date": date_val,
            "total_amount": self._extract_total(),
        }

    def _extract_seller_name(self) -> Optional[str]:
        for line in self.lines_by_position[:20]:
            t = line.get("text", "").strip()
            if any(kw in t.lower() for kw in self.SELLER_KEYWORDS):
                cleaned = re.sub(r"[^a-zA-Z0-9\s\.\,\-\&]", " ", t)
                cleaned = re.sub(r"\s+", " ", cleaned).strip()
                cleaned = re.sub(r"^For\s*[:.]?\s*", "", cleaned, flags=re.IGNORECASE)
                if 3 < len(cleaned) < 100:
                    return cleaned
        if self.lines_by_position:
            first = re.sub(r"[^a-zA-Z0-9\s\.\,\-\&]", " ", self.lines_by_position[0].get("text", ""))
            first = re.sub(r"\s+", " ", first).strip()
            first = re.sub(r"^For\s*[:.]?\s*", "", first, flags=re.IGNORECASE)
            if 3 < len(first) < 100:
                return first
        return None

    def _extract_gst(self) -> Optional[str]:
        m = re.search(self.GST_PATTERN, self.full_text)
        return m.group(0) if m else None

    def _extract_bill_number(self) -> Optional[str]:
        for line in self.ocr_lines:
            for kw in self.BILL_KEYWORDS:
                if kw in line.get("text", "").lower():
                    m = re.search(r"(?:no\.?|#)\s*[:\-]?\s*([A-Za-z0-9\-/]+)", line.get("text", ""), re.IGNORECASE)
                    if m and len(m.group(1).strip()) > 1:
                        return m.group(1).strip()
        m = re.search(r"(?:bill|invoice|inv)\s*(?:no\.?|#)\s*[:\-]?\s*([A-Za-z0-9\-/]+)", self.full_text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_bill_date(self) -> Optional[datetime]:
        for line in self.ocr_lines:
            if any(kw in line.get("text", "").lower() for kw in self.DATE_KEYWORDS):
                d = self._find_date(line.get("text", ""))
                if d:
                    return d
        for pat in self.DATE_PATTERNS:
            m = re.search(pat, self.full_text, re.IGNORECASE)
            if m:
                try:
                    return self._parse_date(m.group(1))
                except Exception:
                    continue
        return None

    def _extract_total(self) -> Optional[float]:
        for line in self.lines_by_position:
            tl = line.get("text", "").lower()
            if any(kw in tl for kw in ["net amount", "net amt", "netamt", "amount payable", "net payable"]):
                for amt in reversed(re.findall(r"([\d,]+\.?\d+)", line.get("text", ""))):
                    v = self._parse_amount(amt)
                    if v and 1 < v < 1000000:
                        return v
        wm = re.search(r"(?:rupees|rs\.?)\s+([A-Z\s]+?)(?:only)?", self.full_text, re.IGNORECASE)
        if wm:
            v = self._words_to_number(wm.group(1).strip())
            if v:
                return v
        if len(self.lines_by_position) >= 4:
            footer = self.lines_by_position[int(len(self.lines_by_position) * 0.75):]
            for line in footer:
                tl = line.get("text", "").lower()
                amts = re.findall(r"(\d{2,}\.\d{2})", line.get("text", ""))
                if any(kw in tl for kw in ["net amount", "grand total", "total amount"]):
                    for a in amts:
                        v = self._parse_amount(a)
                        if v and 10 < v < 1000000:
                            return v
            bottom = []
            for line in footer[-10:]:
                for n in re.findall(r"(\d{3,}\.\d{2})", line.get("text", "")):
                    v = self._parse_amount(n)
                    if v and 10 < v < 1000000:
                        bottom.append(v)
            if bottom:
                return max(bottom)
        return None

    def _parse_inline_prices(self, text: str) -> Optional[Tuple[int, float, float]]:
        """Parse QTY, RATE, AMOUNT from inline text.

        Handles:
          - Space-separated: "10 25.50 255.00"
          - Concatenated (no spaces): "1025.50255.00" → QTY=10, RATE=25.50, AMOUNT=255.00
          - Rate+amount from .XX pairs: extract rate/amount first, then derive qty
        """
        t = text.strip()
        if not t:
            return None

        # Try space-separated first: 3+ numbers
        nums = re.findall(r"\b(\d+\.?\d*)\b", t)
        nums = [n for n in nums if not re.search(rf"\b{n}\s*(?:MG|ML|GM|MCG|IU)\b", t, re.IGNORECASE)]
        if len(nums) >= 3:
            candidate_qty = int(float(nums[-3]))
            candidate_rate = float(nums[-2])
            candidate_amount = float(nums[-1])
            if self._validate_price_trio(candidate_qty, candidate_rate, candidate_amount):
                return (candidate_qty, candidate_rate, candidate_amount)

        # Try patterns like "QTYxRATE=AMOUNT" or "QTY*RATE=AMOUNT"
        m = re.search(r"(\d+)\s*[xX*]\s*(\d+\.?\d*)\s*[=:]?\s*(\d+\.?\d*)", t)
        if m:
            qty = int(m.group(1))
            rate = float(m.group(2))
            amount = float(m.group(3))
            if self._validate_price_trio(qty, rate, amount):
                return (qty, rate, amount)

        # Concatenated format: try each qty length (legacy approach)
        # Handles "1025.50255.00" → qty=10, rate=25.50, amount=255.00
        for qty_end in range(1, min(len(t) - 9, 6) if len(t) > 9 else 0):
            if not t[:qty_end].isdigit():
                break
            remaining = t[qty_end:]
            m = re.match(r"(\d+\.\d{2})(\d+\.\d{2})$", remaining)
            if m:
                qty = int(t[:qty_end])
                rate = float(m.group(1))
                amount = float(m.group(2))
                if self._validate_price_trio(qty, rate, amount):
                    return (qty, rate, amount)

        # Find all .XX pairs and try multi-strategy parsing
        price_pairs = re.findall(r"(\d+\.\d{2})", t)
        if len(price_pairs) >= 2:
            before = t[:t.find(price_pairs[0])]

            # Strategy 1: qty from text-before-first-pair
            if before and before.strip().isdigit():
                qty_before = int(before.strip())
                for ri in range(len(price_pairs)):
                    for ai in range(len(price_pairs)):
                        if ri != ai and self._validate_price_trio(qty_before, float(price_pairs[ri]), float(price_pairs[ai])):
                            return (qty_before, float(price_pairs[ri]), float(price_pairs[ai]))

            # Strategy 2: computed qty = round(amount/rate) when rate has non-zero cents
            for ri in range(len(price_pairs)):
                for ai in range(len(price_pairs)):
                    if ri == ai:
                        continue
                    rv, av = float(price_pairs[ri]), float(price_pairs[ai])
                    if abs(rv - round(rv)) > 0.001:
                        cq = int(round(av / rv))
                        if cq > 0 and self._validate_price_trio(cq, rv, av):
                            return (cq, rv, av)

            # Strategy 3: truncate first pair's integer part as qty
            first_int = price_pairs[0].split('.')[0]
            if first_int.isdigit() and 1 <= len(first_int) <= 3:
                qf = int(first_int)
                for ri in range(1, len(price_pairs)):
                    rv = float(price_pairs[ri])
                    if self._validate_price_trio(qf, rv, qf * rv):
                        return (qf, rv, qf * rv)

        # Fallback: try parsing as RATE + AMOUNT (2 decimal numbers), qty=1
        parts = re.findall(r"(\d+\.?\d*)", t)
        parts = [p for p in parts if not re.search(rf"\b{p}\s*(?:MG|ML|GM|MCG|IU)\b", t, re.IGNORECASE)]
        if len(parts) == 2:
            a, b = float(parts[0]), float(parts[1])
            if a < b:
                if self._validate_price_trio(1, a, b):
                    return (1, a, b)
            elif self._validate_price_trio(1, b, a):
                return (1, b, a)

        return None

    def _validate_price_trio(self, qty: int, rate: float, amount: float) -> bool:
        """Check if qty, rate, amount are consistent."""
        if not (1 <= qty <= 9999 and 1 <= rate <= 99999 and 1 <= amount <= 999999):
            return False
        expected = round(qty * rate, 2)
        # Allow 15% tolerance for OCR rounding
        if abs(expected - amount) / max(amount, 0.01) <= 0.15:
            return True
        return False

    def _parse_amount(self, text: str) -> Optional[float]:
        try:
            v = float(text.replace(",", "").strip())
            return v if 0 < v < 10000000 else None
        except (ValueError, TypeError):
            return None

    def _words_to_number(self, words: str) -> Optional[float]:
        wmap = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
            "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
            "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
            "eighty": 80, "ninety": 90,
            "hundred": 100, "thousand": 1000, "lakh": 100000, "crore": 10000000,
        }
        total = 0
        current = 0
        for token in words.lower().replace("and", "").split():
            token = token.strip(" ,.")
            if token in wmap:
                val = wmap[token]
                if val >= 1000:
                    current *= val
                    total += current
                    current = 0
                elif val >= 100:
                    current *= val
                else:
                    current += val
        total += current
        return total if total > 0 else None

    # ─── Item Extraction ──────────────────────────────────────────

    def _extract_items(self) -> List[Dict]:
        items = self._extract_columnar()
        if items and len(items) >= 2:
            logger.info(f"Columnar: {len(items)} items")
            return items
        items = self._extract_product_centric()
        if items:
            logger.info(f"Product-centric: {len(items)} items")
            return items
        items = self._extract_linear()
        if items:
            logger.info(f"Linear: {len(items)} items")
            return items
        items = self._fallback()
        logger.info(f"Fallback: {len(items)} items")
        return items

    # ─── COLUMNAR EXTRACTION (primary strategy) ──────────────────

    def _extract_columnar(self) -> List[Dict]:
        search_limit = int(len(self.lines_by_position) * 0.5)
        col_headers = []
        for line in self.lines_by_position[:search_limit]:
            tl = line.get("text", "").lower()
            x = line.get("bbox", [[0, 0]])[0][0]
            y = line.get("bbox", [[0, 0]])[0][1]
            for col_name, kws in self.COLUMN_DEFS:
                for kw in kws:
                    if kw in tl:
                        col_headers.append((col_name, x, y))
                        break
        if len(col_headers) < 2:
            return []
        col_headers.sort(key=lambda c: c[1])
        seen = set()
        unique = []
        for name, x, y in col_headers:
            if name not in seen:
                seen.add(name)
                unique.append((name, x, y))
        if len(unique) < 2:
            return []

        header_y = max(c[2] for c in unique)
        section_end = None
        for line in self.lines_by_position:
            y = line.get("bbox", [[0, 0]])[0][1]
            if y > header_y + 10:
                if any(kw in line.get("text", "").lower() for kw in self.NET_TOTAL_KEYWORDS):
                    section_end = y
                    break

        col_data = {}
        for idx, (col_name, col_x, col_y) in enumerate(unique):
            entries = []
            # Detect if this is part of a rightmost column group (same X as everything after)
            is_rightmost = True
            for j in range(idx + 1, len(unique)):
                if unique[j][1] != col_x:
                    is_rightmost = False
                    break
            # Find gaps to columns with different X (skip merged/same-X siblings)
            gap_to_next = 150
            for j in range(idx + 1, len(unique)):
                if unique[j][1] != col_x:
                    gap_to_next = abs(unique[j][1] - col_x)
                    break
            gap_to_prev = 150
            for j in range(idx - 1, -1, -1):
                if unique[j][1] != col_x:
                    gap_to_prev = abs(col_x - unique[j][1])
                    break
            # Rightmost columns need wider tolerance (prices are far right of headers)
            # Non-rightmost columns use 80% of min gap with 100px floor
            if is_rightmost:
                tolerance = 150
            else:
                tolerance = max(min(gap_to_next, gap_to_prev) * 0.8, 100)

            for line in self.lines_by_position:
                y = line.get("bbox", [[0, 0]])[0][1]
                x = line.get("bbox", [[0, 0]])[0][0]
                text = line.get("text", "").strip()
                if y <= col_y + 10:
                    continue
                if section_end and y >= section_end:
                    continue
                if abs(x - col_x) > tolerance:
                    continue
                if len(text) < 1 or (len(text) < 2 and col_name not in ("quantity", "rate", "amount")):
                    continue
                if self._is_noise(text):
                    continue
                if not self._valid_for_col(col_name, text):
                    continue
                entries.append((y, text))

            entries.sort(key=lambda e: e[0])
            col_data[col_name] = [e for _, e in entries]

        if not col_data:
            return []
        if "product" in col_data:
            num_items = len(col_data["product"])
        else:
            ref = max(col_data.keys(), key=lambda k: len(col_data[k]))
            num_items = len(col_data[ref])
        if num_items < 1 or num_items > 100:
            return []

        items = []
        col_keys = [c[0] for c in unique if c[0] in col_data]
        for i in range(num_items):
            item = {"product_name": None, "batch_id": None, "expiry_date": None,
                    "quantity": None, "unit_price": None, "total_price": None}
            for col_name in col_keys:
                if i < len(col_data[col_name]):
                    value = self._parse_col_val(col_name, col_data[col_name][i])
                    if value is not None:
                        self._set_field(item, col_name, value)
            if item["product_name"]:
                item["product_name"] = re.sub(r"[^a-zA-Z0-9\s\.\-\(\)]", " ", item["product_name"])
                item["product_name"] = re.sub(r"\s+", " ", item["product_name"]).strip()
                if len(item["product_name"]) >= 3:
                    items.append(item)
        return items

    def _is_noise(self, text: str) -> bool:
        tl = text.lower().strip()
        patterns = [
            r"^(s\.?no|sr\.?no)$", r"^(batch|exp|qty|rate|amount|mrp|hsn|total|net|disc|tax)\.?$",
            r"^(gst|cgst|sgst|igst)\.?$", r"^(store|cash|mob|date)$",
            r"^(round\s*off|round)$", r"^(less|ret|add)$",
            r"^(please|see|backside)$",
        ]
        return any(re.match(p, tl) for p in patterns)

    def _valid_for_col(self, col_name: str, text: str) -> bool:
        if col_name == "product":
            return bool(re.search(r"[A-Za-z]{3,}", text)) and not re.match(r"^\d", text)
        elif col_name == "batch":
            return bool(re.search(r"[A-Za-z]", text)) and len(text) >= 2
        elif col_name == "expiry":
            # Reject long strings (batch codes with embedded dates like "BTH23A1205/2027")
            if len(text) > 12:
                return False
            return bool(re.search(r"\d{1,2}[/-]\d{1,2}", text) or re.search(r"[A-Z]{3}\d{2}", text, re.IGNORECASE))
        elif col_name == "quantity":
            return bool(re.match(r"^[\d\.]+$", text.strip()))
        elif col_name in ("rate", "amount"):
            # Must look like a price: digits/dots only, optionally with currency prefix
            return bool(re.match(r"^[₹Rs\.\$\s]*[\d][\d\.]*\s*$", text.strip()))
        return True

    def _parse_col_val(self, col_name: str, text: str) -> Optional[Any]:
        if col_name == "product":
            c = re.sub(r"[^a-zA-Z0-9\s\.\-\(\)]", " ", text)
            c = re.sub(r"\s+", " ", c).strip()
            return c if len(c) > 2 else None
        elif col_name == "batch":
            return re.sub(r"[^A-Za-z0-9\-/]", "", text) or None
        elif col_name == "expiry":
            return self._parse_expiry(text)
        elif col_name == "quantity":
            inline = self._parse_inline_prices(text)
            if inline:
                return inline[0]
            m = re.search(r"(\d+\.?\d*)", text)
            return int(float(m.group(1))) if m else None
        elif col_name == "rate":
            inline = self._parse_inline_prices(text)
            if inline:
                return inline[1]
            m = re.search(r"(\d+\.?\d*)", text)
            return float(m.group(1)) if m else None
        elif col_name == "amount":
            inline = self._parse_inline_prices(text)
            if inline:
                return inline[2]
            m = re.search(r"(\d+\.?\d*)", text)
            return float(m.group(1)) if m else None
        return None

    def _set_field(self, item: Dict, col: str, val: Any):
        mapping = {"product": "product_name", "batch": "batch_id", "expiry": "expiry_date",
                   "quantity": "quantity", "rate": "unit_price", "amount": "total_price"}
        key = mapping.get(col)
        if key:
            item[key] = val

    # ─── PRODUCT-CENTRIC EXTRACTION (secondary) ──────────────────

    def _extract_product_centric(self) -> List[Dict]:
        product_indices = []
        for i, line in enumerate(self.lines_by_position):
            if self._is_medicine(line.get("text", "")):
                product_indices.append((i, line))

        if not product_indices:
            return []

        section_end = len(self.lines_by_position)
        for i in range(product_indices[0][0], len(self.lines_by_position)):
            if any(kw in self.lines_by_position[i].get("text", "").lower() for kw in self.NET_TOTAL_KEYWORDS):
                section_end = i
                break

        items = []
        for idx, line in product_indices:
            if idx >= section_end:
                break
            item = {"product_name": self._clean_product(line.get("text", "")),
                    "batch_id": None, "expiry_date": None,
                    "quantity": None, "unit_price": None, "total_price": None}
            if not item["product_name"]:
                continue

            # Try to extract inline numbers from the same line (e.g. "Paracetamol 500mg 10 25.50 255.00")
            # Also handle concatenated prices like "1025.50255.00" (QTY RATE AMOUNT merged)
            line_text = line.get("text", "")
            parsed = self._parse_inline_prices(line_text)
            if parsed:
                item["quantity"] = parsed[0]
                item["unit_price"] = parsed[1]
                item["total_price"] = parsed[2]
                items.append(item)
                continue

            prod_y = line.get("bbox", [[0, 0]])[0][1]
            prod_x = line.get("bbox", [[0, 0]])[0][0]
            next_prod_y = float('inf')
            for j in range(idx + 1, len(self.lines_by_position)):
                if self._is_medicine(self.lines_by_position[j].get("text", "")):
                    next_prod_y = self.lines_by_position[j].get("bbox", [[0, 0]])[0][1]
                    break
            max_y = min(prod_y + 120, next_prod_y - 5) if next_prod_y != float('inf') else prod_y + 120
            nearby = self.lines_by_position[max(0, idx - 3):min(len(self.lines_by_position), idx + 20)]
            # Collect all data from nearby lines before assigning
            price_candidates = []
            for nl in nearby:
                if nl is line:
                    continue
                ny = nl.get("bbox", [[0, 0]])[0][1]
                if ny < prod_y - 5 or ny > max_y:
                    continue
                text = nl.get("text", "").strip()
                if not text:
                    continue
                # Allow single-digit quantities (e.g. "5") but skip pure punctuation
                if len(text) == 1 and not text.isdigit():
                    continue
                exp = self._parse_expiry(text)
                if exp and item["expiry_date"] is None:
                    item["expiry_date"] = exp
                    continue
                batch = self._detect_batch(text)
                if batch and item["batch_id"] is None:
                    item["batch_id"] = batch
                    continue
                inline = self._parse_inline_prices(text)
                if inline:
                    price_candidates.extend([inline[0], inline[1], inline[2]])
                    continue
                nm = re.match(r"^[₹Rs\.$\s]*(\d+\.?\d*)\s*$", text, re.IGNORECASE)
                if not nm:
                    nm = re.match(r"^(\d+\.?\d*)\s*$", text)
                if nm:
                    try:
                        price_candidates.append(float(nm.group(1)))
                    except ValueError:
                        pass
            # Assign price candidates: smallest value is qty, largest is total_price
            if price_candidates:
                sorted_vals = sorted(price_candidates)
                if len(sorted_vals) >= 3:
                    if item["quantity"] is None and sorted_vals[0] == int(sorted_vals[0]):
                        item["quantity"] = int(sorted_vals[0])
                    if item["unit_price"] is None:
                        item["unit_price"] = sorted_vals[1]
                    if item["total_price"] is None:
                        item["total_price"] = sorted_vals[-1]
                elif len(sorted_vals) == 2:
                    if item["unit_price"] is None:
                        item["unit_price"] = sorted_vals[0]
                    if item["total_price"] is None:
                        item["total_price"] = sorted_vals[1]
                elif len(sorted_vals) == 1:
                    v = sorted_vals[0]
                    if v == int(v) and v < 100:
                        if item["quantity"] is None:
                            item["quantity"] = int(v)
                    else:
                        if item["total_price"] is None:
                            item["total_price"] = v
            if item["product_name"]:
                items.append(item)
        return items

    def _is_medicine(self, text: str) -> bool:
        if len(text) < 4:
            return False
        if re.match(r"^\d+\s*(GM|ML|MG|TAB|CAP|SYP|INJ)\.?$", text.strip(), re.IGNORECASE):
            return False
        if re.match(r"^(VIAL|AMP|PFS|DUP|STRIP|BOX|BOTTLE)\.?$", text.strip(), re.IGNORECASE):
            return False
        if re.search(self.MEDICINE_SUFFIXES, text, re.IGNORECASE):
            prefix = re.split(self.MEDICINE_SUFFIXES, text, flags=re.IGNORECASE)[0].strip()
            if len(prefix) >= 2:
                return not bool(re.match(r"^[A-Z]{1,3}\d", prefix))
            return False
        if not re.search(r"[A-Za-z]{4,}", text):
            return False
        if re.match(r"^[A-Z]{1,3}\d", text) or re.match(r"^\d", text):
            return False
        lower = text.lower().strip()
        if any(ew in lower for ew in self.EXCLUDE_WORDS):
            return False
        if not re.search(r"[aeiouAEIOU]", text):
            return False
        return True

    def _clean_product(self, text: str) -> Optional[str]:
        c = re.sub(r"[^a-zA-Z0-9\s\.\-\(\)]", " ", text)
        c = re.sub(r"\s+", " ", c).strip()
        return c if len(c) > 2 else None

    def _classify_line(self, text: str, nx: float, ny: float, px: float, py: float) -> Optional[Tuple]:
        expiry = self._parse_expiry(text)
        if expiry:
            return ("expiry_date", expiry)

        batch = self._detect_batch(text)
        if batch:
            return ("batch_id", batch)

        # Try to extract numeric value from price-like text (with currency symbols)
        t = text.strip()
        price_match = re.match(r"^[₹Rs\.$\s]*(\d+\.?\d*)\s*$", t, re.IGNORECASE)
        if not price_match:
            price_match = re.match(r"^(\d+\.?\d*)\s*$", t)
        nm = price_match or re.match(r"^(\d+\.?\d*)$", t)
        if nm:
            try:
                val = float(nm.group(1))
                if val == int(val) and val < 100:
                    return ("quantity", int(val))
                if 0 < val < 100000:
                    if nx > px + 50:
                        return ("total_price", val)
                    return ("unit_price", val)
            except ValueError:
                pass
        return None

    # ─── IMPROVED BATCH DETECTION ────────────────────────────────
    #
    # Batch numbers have these characteristics:
    #   - Alphanumeric (letters + digits), typically 4-8 chars
    #   - Often start with 1-3 letters followed by 2-5 digits (e.g., "AB11", "BTH12345")
    #   - Usually NOT long numeric-only codes (which tend to be product codes/SKUs)
    #   - Usually NOT pure numeric inventory codes
    #   - Positionally near expiry column or under "Batch"/"B.No"/"Lot" header
    #
    # Product codes / SKUs tend to be:
    #   - Long numeric strings (6+ digits)
    #   - Pure digits
    #   - Near the product name (often prefixed)
    #
    # Strategy: prefer short alphanumeric near expiry/quantiy columns over pure-digit codes.

    def _detect_batch(self, text: str) -> Optional[str]:
        t = text.strip()

        # If explicitly labeled with batch keyword, extract it
        for kw in self.BATCH_KEYWORDS:
            if kw in t.lower():
                m = re.search(r"(?:batch|b\.?no|lot)\s*[:\-]?\s*([A-Za-z0-9\-/]+)", t, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    if 2 <= len(val) <= 12:
                        return val

        # Pattern 1: Short alphanumeric starting with letters (classic batch format)
        # e.g., AB11, BTH12345, JB36, WE05, NK23, E157
        m = re.match(r"^([A-Z]{1,4}\d{1,6})$", t, re.IGNORECASE)
        if m:
            val = m.group(1)
            if 2 <= len(val) <= 10:
                return val.upper()

        # Pattern 2: Letter then digits then letter (e.g., A123B)
        m = re.match(r"^([A-Za-z]\d{2,6}[A-Za-z]\d*)$", t)
        if m:
            val = m.group(1)
            if 3 <= len(val) <= 10:
                return val.upper()

        # Pattern 3: Pure digits - ONLY if length is 3-5 (short batch codes)
        # Reject 6+ digit pure numbers - those are likely product codes/SKUs
        m = re.match(r"^(\d{3,5})$", t)
        if m:
            return m.group(1)

        # Reject: 6+ digit numbers (product codes), single chars, long strings
        return None

    # ─── LINEAR EXTRACTION (tertiary) ────────────────────────────

    def _extract_linear(self) -> List[Dict]:
        items = []
        in_section = False
        for line in self.lines_by_position:
            tl = line.get("text", "").lower()
            if any(kw in tl for kw in ["s.no", "sr.no", "item", "product", "description", "particulars"]):
                in_section = True
                continue
            if any(kw in tl for kw in self.NET_TOTAL_KEYWORDS):
                in_section = False
                continue
            if in_section and self._is_product_line(line.get("text", "")):
                item = self._parse_item_line(line.get("text", ""))
                if item:
                    items.append(item)
        return items

    def _is_product_line(self, text: str) -> bool:
        t = text.strip()
        if len(t) < 5:
            return False
        if re.match(r"^\d+\.?\d*$", t):
            return False
        lower = t.lower()
        if any(ew in lower for ew in self.EXCLUDE_WORDS):
            return False
        if re.search(self.MEDICINE_SUFFIXES, t, re.IGNORECASE):
            return True
        if not re.search(r"[A-Za-z]{4,}", t):
            return False
        if re.match(r"^[A-Z]{1,3}\d", t):
            return False
        words = t.split()
        if len(words) >= 4:
            return True
        if re.search(r"\d", t):
            return True
        return False

    def _parse_item_line(self, text: str) -> Optional[Dict]:
        pat1 = r"(\d+)\s+([A-Za-z0-9\s\.\-\(\)]+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
        pat2 = r"([A-Za-z][A-Za-z0-9\s\.\-]{2,})\s+(\d+)\s*[\*xX]\s*([\d,]+\.?\d*)\s*=?\s*([\d,]+\.?\d*)"
        for pat in [pat1, pat2]:
            m = re.search(pat, text)
            if m:
                g = m.groups()
                if len(g) == 5:
                    return {"product_name": g[1].strip(), "quantity": int(g[0]),
                            "unit_price": float(g[2].replace(",", "")), "total_price": float(g[4].replace(",", ""))}
                if len(g) == 4:
                    return {"product_name": g[0].strip(), "quantity": 1,
                            "unit_price": float(g[2].replace(",", "")), "total_price": float(g[3].replace(",", ""))}
        return None

    # ─── FALLBACK ────────────────────────────────────────────────

    def _fallback(self) -> List[Dict]:
        items = []
        in_section = False
        for line in self.lines_by_position:
            tl = line.get("text", "").lower()
            if any(kw in tl for kw in ["s.no", "sr.no", "item", "product"]):
                in_section = True
                continue
            if any(kw in tl for kw in self.NET_TOTAL_KEYWORDS):
                in_section = False
                continue
            if in_section and line.get("confidence", 0) > 0.5 and self._is_product_line(line.get("text", "")):
                nums = re.findall(r"[\d,]+\.?\d+", line.get("text", ""))
                if nums:
                    prod = re.sub(r"[\d,]+\.?\d*", "", line.get("text", "")).strip()
                    prod = re.sub(r"[^a-zA-Z\s\.\-]", "", prod).strip()
                    if prod and len(prod) > 2:
                        vals = [float(n.replace(",", "")) for n in nums]
                        items.append({
                            "product_name": prod,
                            "quantity": int(vals[0]) if len(vals) > 1 and vals[0] == int(vals[0]) else 1,
                            "unit_price": vals[-2] if len(vals) > 1 else vals[0],
                            "total_price": vals[-1],
                        })
        return items

    # ─── PARSING HELPERS ─────────────────────────────────────────

    def _parse_expiry(self, text: str) -> Optional[str]:
        m = re.search(r"(?:exp\.?\s*)?(\d{1,2})[/-](\d{2})\b", text, re.IGNORECASE)
        if m:
            mo, yr = int(m.group(1)), int(m.group(2))
            if 1 <= mo <= 12 and 20 <= yr <= 35:
                return f"{mo:02d}/{yr:02d}"
        m = re.search(r"(?:exp\.?\s*)?(\d{1,2})[/-](\d{4})\b", text, re.IGNORECASE)
        if m:
            mo, yr = int(m.group(1)), int(m.group(2))
            if 1 <= mo <= 12 and 2020 <= yr <= 2035:
                return f"{mo:02d}/{yr % 100:02d}"
        m = re.search(r"(?:exp\.?\s*)?([A-Z]{3})(\d{2})\b", text, re.IGNORECASE)
        if m:
            ms, yr = m.group(1).lower(), int(m.group(2))
            if ms in self.MONTH_MAP and 20 <= yr <= 35:
                return f"{self.MONTH_MAP[ms]}/{yr:02d}"
        return None

    def _find_date(self, text: str) -> Optional[datetime]:
        for pat in self.DATE_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    return self._parse_date(m.group(1))
                except Exception:
                    continue
        return None

    def _parse_date(self, s: str) -> Optional[datetime]:
        s = s.strip()
        m = re.match(r"\d{1,2}[/-]\d{1,2}[/-](\d{2})$", s)
        if m and int(m.group(1)) <= 30:
            s = re.sub(r"(\d{2})$", r"20\1", s)
        try:
            p = date_parser.parse(s, dayfirst=True)
            if p.year < 100:
                p = p.replace(year=p.year + 2000)
            if 2000 <= p.year <= 2035:
                return p
        except Exception:
            pass
        return None
