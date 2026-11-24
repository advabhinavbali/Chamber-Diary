#!/usr/bin/env python3
"""
court_sync.py — pull the Punjab & Haryana High Court daily cause list,
find the matters that belong to you, and write:

    docs/data.json   machine-readable matches (the app reads this)
    docs/diary.ics   a calendar feed Google Calendar can subscribe to
    docs/causelist.txt  a plain list you can read on your phone

No login, no captcha, no API key. Public court data only.

Usage:
    python court_sync.py                 # today .. today+2
    python court_sync.py --days 5
    python court_sync.py --date 2026-11-25
    python court_sync.py --pdf file.pdf --date 2026-11-23   # offline test
"""
import argparse, datetime as dt, json, os, re, sys, urllib.parse, urllib.request

BASE = "https://highcourtchd.gov.in"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))   # court dates are IST

def today_ist():
    return dt.datetime.now(IST).date()

# ---------------------------------------------------------------- fetching
def http_post(path, fields, timeout=120):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE + "/?mod=causelist",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def http_get_bytes(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def list_links(date_obj, list_type="B"):
    """Ask the court which cause-list files exist for a date.
    list_type 'B' = complete list (one PDF with every bench)."""
    html = http_post("/view_causeList.php", {
        "t_f_date": date_obj.strftime("%d/%m/%Y"),
        "urg_ord": list_type,
        "action": "show_causeList",
    })
    if "!~~!" not in html:
        return []
    body = html.split("!~~!", 1)[1]
    out, seen = [], set()
    for m in re.finditer(r"show_cause_list\.php\?filename=([A-Za-z0-9]+)", body):
        fn = m.group(1)
        if fn in seen:
            continue
        seen.add(fn)
        out.append(BASE + "/show_cause_list.php?filename=" + fn)
    return out

# ---------------------------------------------------------------- parsing
CASE_RE = re.compile(r"\b[A-Z]{2,8}(?:-[A-Z]{1,3})?-\d{1,6}-\d{4}\b")
ITEM_RE = re.compile(r"^(\d{1,4})\b")
BENCH_RE = re.compile(r"^HON[’'`]?\s*BLE\s+((?:THE\s+)?(?:MR|MS|MRS|DR)?\.?\s*(?:JUSTICE|CHIEF|ACTING|JUDGE|SENIOR).*)", re.I)
HEADING_RE = re.compile(r"(MOTION PETITION|CAUSE LIST|LIST FOR THE|DATED\s+\d{2}/\d{2}/\d{4})", re.I)
COURT_RE = re.compile(r"CR\s*NO\.?\s*(\d+)", re.I)
DATE_IN_HEAD_RE = re.compile(r"DATED\s+(\d{2})/(\d{2})/(\d{4})", re.I)

def page_lines(page):
    """Return [(x0, y0, text)] for every visible line on the page."""
    out = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if txt:
                out.append((line["bbox"][0], line["bbox"][1], txt))
    out.sort(key=lambda t: (round(t[1], 1), t[0]))
    return out

def parse_pdf(pdf_bytes, list_label="", source=""):
    """Yield one dict per listed entry. Notice pages are skipped: a page only
    counts if it carries a list heading, so stray "Hon'ble" mentions in the
    court's notices never leak into the bench name."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    entries = []
    carry = {"bench": "", "court_no": "", "heading": "", "list_kind": ""}

    for pno in range(doc.page_count):
        lines = page_lines(doc[pno])
        if not lines:
            continue

        # a page is a list page only if it has a heading like
        # "URGENT D.B. I MOTION PETITION FOR THE MONDAY DATED 23/11/2026  CR NO 1"
        head_i = None
        for i, (x0, y0, txt) in enumerate(lines):
            if HEADING_RE.search(txt):
                head_i = i
                break

        if head_i is not None:
            # first page of a bench's list: read the heading, reset the bench
            hx0, hy0, htxt = lines[head_i]
            court_no = carry["court_no"]
            mc = COURT_RE.search(htxt)
            if mc:
                court_no = mc.group(1)
            list_kind = carry["list_kind"]
            u = htxt.upper()
            if "URGENT" in u:
                list_kind = "Urgent"
            elif "ORDINARY" in u:
                list_kind = "Ordinary"
            elif "REGULAR" in u:
                list_kind = "Regular"
            elif "COMPLETE" in u:
                list_kind = "Complete"
            heading = htxt
            bench_names = []
            start_i = head_i + 1
        else:
            # continuation page: same bench, same court, no repeated heading
            serial_col = sum(1 for x0, y0, txt in lines
                             if ITEM_RE.match(txt) and x0 < 60)
            page_text = " ".join(t for _, _, t in lines)
            if serial_col < 2 or not CASE_RE.search(page_text.upper()):
                continue
            court_no = carry["court_no"]
            list_kind = carry["list_kind"]
            heading = carry["heading"]
            bench_names = carry["bench"].split(" & ") if carry["bench"] else []
            start_i = 0

        cur = None
        block = []

        def flush():
            nonlocal block, cur
            if cur is not None and block:
                entries.append(build_entry(
                    cur, block, " & ".join(bench_names), court_no, heading,
                    list_kind, list_label, source, pno + 1))
            block = []

        for x0, y0, txt in lines[start_i:]:
            bm = BENCH_RE.match(txt)
            if bm and len(bench_names) < 3 and 90 <= x0 and len(txt) < 110:
                bench_names.append("Hon'ble " + bm.group(1).strip(" ."))
                continue
            im = ITEM_RE.match(txt)
            if im and x0 < 60:                    # the serial-number column
                flush()
                cur = {"item": int(im.group(1)), "district": ""}
                rest = txt[im.end():].strip()
                if rest:
                    cur["district"] = rest.replace("*", "").strip()
                block = [(x0, txt)]
                continue
            if cur is not None:
                block.append((x0, txt))
        flush()

        carry = {"bench": " & ".join(bench_names), "court_no": court_no,
                 "heading": heading, "list_kind": list_kind}
    return entries


def build_entry(cur, block, bench, court_no, heading, list_kind, list_label, source, page):
    joined = " ".join(t for _, t in block)
    joined = re.sub(r"-\s+(\d{4})", r"-\1", joined)          # rejoin split years
    joined = re.sub(r"-\s+(CWPIL|CWP|CRM|CRR|CRA|FAO|COCP|RSA|RFA|CR)\b", r"-\1", joined)
    cases = CASE_RE.findall(joined.upper())
    # party columns: middle column holds the parties, right column the advocate
    parties = " ".join(t for x0, t in block if 250 <= x0 < 450)
    advocate = " ".join(t for x0, t in block if x0 >= 450)
    return {
        "item": cur["item"], "district": cur["district"],
        "cases": list(dict.fromkeys(cases)),
        "parties": re.sub(r"\s+", " ", parties).strip(" ,")[:220],
        "advocate": re.sub(r"\s+", " ", advocate).strip(" ,"),
        "bench": bench, "court_no": court_no, "list_kind": list_kind,
        "list_label": list_label, "source": source, "page": page,
        "raw": re.sub(r"\s+", " ", joined)[:400],
    }

# ---------------------------------------------------------------- matching
def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

def name_hit(needle, hay):
    """Loose party-name match: every word of 3+ letters must appear."""
    words = [w for w in re.split(r"[^A-Za-z]+", (needle or "").upper()) if len(w) >= 3]
    if not words:
        return False
    hay = (hay or "").upper()
    return all(w in hay for w in words)

def match_entries(entries, cases):
    hits = []
    for e in entries:
        e_cases_norm = [norm(c) for c in e["cases"]]
        for c in cases:
            why = None
            if c.get("caseNo"):
                target = norm(c["caseNo"])
                if any(target == t for t in e_cases_norm):
                    why = "case number"
                elif target and any(target in t or t in target for t in e_cases_norm if len(t) > 8):
                    why = "case number (partial)"
            if not why and not c.get("caseNo") and (c.get("client") or c.get("opposite")):
                if name_hit(c.get("client"), e["parties"]) and (
                        not c.get("opposite") or name_hit(c["opposite"], e["parties"])):
                    why = "party names"
            if why:
                hits.append({
                    "date": e["date"], "item": e["item"], "court_no": e["court_no"],
                    "bench": e["bench"], "list_kind": e["list_kind"],
                    "list_label": e["list_label"],
                    "district": e["district"], "parties": e["parties"],
                    "advocate": e["advocate"], "case_no_in_list": ", ".join(e["cases"]),
                    "matched_by": why, "page": e["page"], "source": e["source"],
                    "case_id": c.get("id", ""), "case_label": c.get("label", "") or c.get("caseNo", ""),
                })
    # de-duplicate: same case + same date + same item
    seen, out = set(), []
    for h in hits:
        k = (h["case_label"], h["date"], h["item"], h["court_no"])
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out

# ---------------------------------------------------------------- outputs
def build_ics(hits, cal_name="Court Diary"):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Court Sync//PHHC//EN",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:" + cal_name, "X-WR-TIMEZONE:Asia/Kolkata"]
    for h in sorted(hits, key=lambda x: (x["date"], x["item"])):
        d = h["date"].replace("-", "")
        end = (dt.date.fromisoformat(h["date"]) + dt.timedelta(days=1)).strftime("%Y%m%d")
        title = f"{h['case_label'] or h['case_no_in_list']} — {h['bench'] or 'PHHC'}"
        desc = (f"Item {h['item']} · CR NO {h['court_no']}\n"
                f"Bench: {h['bench']}\nParties: {h['parties']}\n"
                f"List: {h['list_kind']} ({h['list_label']})\n"
                f"Case no in list: {h['case_no_in_list']}\n— court sync")
        L += ["BEGIN:VEVENT",
              f"UID:sync-{norm(h['case_label'] or h['case_no_in_list'])}-{d}@court-sync",
              "DTSTAMP:" + stamp,
              "DTSTART;VALUE=DATE:" + d, "DTEND;VALUE=DATE:" + end,
              "SUMMARY:" + ics_esc(title),
              "LOCATION:" + ics_esc("Punjab & Haryana High Court, CR NO " + str(h["court_no"])),
              "DESCRIPTION:" + ics_esc(desc),
              "STATUS:CONFIRMED", "TRANSP:TRANSPARENT",
              "BEGIN:VALARM", "TRIGGER:-PT15H", "ACTION:DISPLAY",
              "DESCRIPTION:" + ics_esc("Listed tomorrow: " + (h["case_label"] or "")), "END:VALARM",
              "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"

def ics_esc(s):
    return (str(s or "").replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))

def build_text(hits, dates):
    out = ["P&H HIGH COURT — your matters", ""]
    if not hits:
        out.append("No matter of yours found in the lists pulled for " + ", ".join(dates) + ".")
        return "\n".join(out) + "\n"
    for h in sorted(hits, key=lambda x: (x["date"], x["item"])):
        out.append(f"{h['date']}  ·  CR NO {h['court_no']}  ·  item {h['item']}")
        out.append(f"   {h['case_label'] or h['case_no_in_list']}")
        out.append(f"   {h['bench']}")
        out.append(f"   {h['parties']}")
        out.append("")
    return "\n".join(out)

# ---------------------------------------------------------------- main
def load_cases():
    p = os.path.join(HERE, "cases.json")
    if not os.path.exists(p):
        sys.exit("cases.json not found next to court_sync.py")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", data) if isinstance(data, dict) else data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="how many days ahead to pull")
    ap.add_argument("--date", help="single date YYYY-MM-DD")
    ap.add_argument("--pdf", help="parse a local PDF instead of downloading")
    ap.add_argument("--list-type", default="B", help="B=complete, 1=all, R=regular…")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()

    if a.date:
        dates = [dt.date.fromisoformat(a.date)]
    else:
        today = today_ist()
        dates = [today + dt.timedelta(days=i) for i in range(a.days)]

    cases = load_cases()
    all_entries, hits, used = [], [], []

    if a.pdf:
        with open(a.pdf, "rb") as f:
            pdf = f.read()
        d = dates[0].isoformat()
        entries = parse_pdf(pdf, "local", os.path.basename(a.pdf))
        for e in entries:
            e["date"] = d
        all_entries += entries
        used.append(d)
    else:
        for day in dates:
            links = list_links(day, a.list_type)
            if not links:
                print(f"{day}: no cause list published yet")
                continue
            print(f"{day}: {len(links)} file(s)")
            used.append(day.isoformat())
            for url in links:
                try:
                    pdf = http_get_bytes(url)
                except Exception as ex:
                    print("  download failed:", ex)
                    continue
                entries = parse_pdf(pdf, a.list_type, os.path.basename(url)[:60])
                for e in entries:
                    e["date"] = day.isoformat()
                all_entries += entries
                print(f"  parsed {len(entries)} entries from {len(pdf)//1024} KB")

    for e in all_entries:
        if not e["bench"]:
            e["bench"] = ""
    hits = match_entries(all_entries, cases)
    os.makedirs(a.out, exist_ok=True)
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "court": "Punjab & Haryana High Court",
        "dates_pulled": used,
        "entries_scanned": len(all_entries),
        "matches": hits,
    }
    with open(os.path.join(a.out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.out, "diary.ics"), "w", encoding="utf-8", newline="") as f:
        f.write(build_ics(hits))
    with open(os.path.join(a.out, "causelist.txt"), "w", encoding="utf-8") as f:
        f.write(build_text(hits, used))
    print(f"entries scanned: {len(all_entries)} | your matches: {len(hits)}")
    for h in hits:
        print(f"  {h['date']} CR {h['court_no']} item {h['item']} — {h['case_label'] or h['case_no_in_list']} ({h['matched_by']})")

if __name__ == "__main__":
    main()
