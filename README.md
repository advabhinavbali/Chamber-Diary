# Court Diary — your case diary with automatic cause-list sync

Two things in one repository:

1. **The app** (`docs/index.html`) — your offline case diary: cases, hearing diary,
   orders to read, notes, printable cause lists. Installs to your phone's home screen.
2. **The sync** (`court_sync.py` + GitHub Actions) — every day it downloads the
   Punjab & Haryana High Court cause list, finds the matters that are yours, and
   writes the court number, item number and bench into the app and into a calendar
   feed you can subscribe to in Google Calendar.

Cost: ₹0. No server of your own, no subscription, no API key.

---

## What it does and does not do

**In the app (all offline, all on your device):**
- Case register — case number, CNR, court, room, parties, stage, our side, tags
- **Hearing diary** — what happened on each date, purpose for the next
- **To do** — per-case tasks with due date and priority; a global list, overdue first
- **Documents** — upload and open PDFs and images against a case (vakalatnama, plaint,
  evidence, orders, judgments), labelled by kind, saved in the browser's own storage
- **Orders** — date, bench, the operative part, PDF link, read/unread tracking
- **Notes** — pinned, timestamped, per case
- **Fees** — a simple ledger per case: billed, received, balance; practice-wide totals
- **Clients** — built from the register, with phone and their matters
- **Schedule** — the next six weeks: hearings, deadlines and court listings on one page
- **Alerts** — passed dates, overdue tasks, unread orders, matters listed today
- Printable cause list, brief top, WhatsApp-ready list text, CSV in/out, JSON backup

**Automatic (from the daily sync):**
- Which of your matters are listed, on which date
- Court number (CR NO), item/serial number, bench, list type (Urgent/Ordinary/…)
- A calendar event per listing, with a reminder at 9 am the previous day
- Runs twice a day by itself (≈06:15 and ≈19:45 IST)

**Not automatic (and why):**
- **Case status / next date / orders passed.** Those sit behind the case-status
  search, which needs a captcha, and behind logins on the new portal. Anything
  that fills a captcha automatically is both unreliable and against the site's
  terms, so this kit does not do it. You enter the next date from the order — the
  app keeps the diary; the sync keeps you honest about *today's* list.
- **Push notifications when the app is closed.** A web app with no server cannot
  do that. Reminders come from Google Calendar; in-app alerts are always on.
- **Other courts.** This release reads the P&H High Court only.
- **Your files in the backup.** Uploaded documents live in the browser's storage
  and are not inside the JSON backup — keep originals in Drive too. If an upload
  ever refuses to save, open the app from its https address; some browsers restrict
  storage for local files.

The court's own list always governs. Treat the app as a head start, not a substitute
for checking the display board and the supplementary list.

---

## One-time setup (about 15 minutes)

You need a free GitHub account. Nothing else.

### 1. Create the repository
1. Sign up / sign in at https://github.com
2. Top-right **+** → **New repository**
3. Name: `court-diary`. Set it **Public** (Pages and Actions are free on public
   repos). Do **not** add a README. → **Create repository**

### 2. Upload these files
1. On the empty repo page click **uploading an existing file**
2. Unzip `court-diary-sync-kit.zip` and drag **everything inside the folder** into
   the browser — including the `.github` folder and the `docs` folder
3. Commit changes

> If `.github` did not upload (some browsers skip dotted folders), use
> **Add file → Create new file**, type `.github/workflows/court-sync.yml` as the
> name, and paste the contents of that file from the zip.

### 3. Put your cases in
Open `cases.json` → pencil icon → replace the example with your matters:

```json
{
  "advocate": "Abhinav Bali",
  "cases": [
    { "id": "1", "label": "CWP-1234-2024", "caseNo": "CWP-1234-2024",
      "client": "Ram Kumar", "opposite": "State of Punjab" }
  ]
}
```

Easier: open the app → **Settings → Court sync → Export cases.json**, then upload
that file over `cases.json` in the repo.

`caseNo` is what the matcher trusts — write it exactly as the court writes it
(`CWP-1234-2024`, `CRM-M-12345-2024`, `CRA-D-456-2023`). A case with no `caseNo`
is matched on the two party names instead, which is looser.

### 4. Turn on the web page
**Settings → Pages** → *Build and deployment* → Source: **Deploy from a branch** →
Branch: **main**, Folder: **/docs** → **Save**.
After a minute your app is at `https://<your-username>.github.io/court-diary/`

### 5. Run the sync once
**Actions** tab → if asked, click *I understand my workflows, go ahead and enable
them* → **Court diary sync** → **Run workflow** → **Run workflow**.
Wait ~2 minutes. `docs/data.json` will appear in the repo and the app will show a
**From the court's cause list** card.

### 6. Put it on your phone
Open your `github.io` link → iPhone: Share → *Add to Home Screen*; Android: menu →
*Install app*.

### 7. Subscribe in Google Calendar (one time, then it keeps itself updated)
Google Calendar on a laptop → **Other calendars +** → **From URL** → paste:

```
https://<your-username>.github.io/court-diary/diary.ics
```

→ **Add calendar**. Every listing becomes an all-day event with a 9 am reminder the
day before. It refreshes by itself — no importing, no duplicates.

---

## Daily use

Nothing to do. Open the app in the morning: the court card shows today's items,
the case page shows *Listed 23 Nov 2026 · CR NO 1 · item 101*, and Google Calendar
has already reminded you the evening before.

---

## Files

| File | What it is |
|---|---|
| `docs/index.html` | the app (works offline, installs to home screen) |
| `docs/data.json` | written by the sync: your listings, with court/item/bench |
| `docs/diary.ics` | the calendar feed Google Calendar subscribes to |
| `docs/causelist.txt` | plain text list, easy to read or forward on WhatsApp |
| `cases.json` | your case list — the only file you edit |
| `court_sync.py` | the reader: downloads the cause-list PDFs and parses them |
| `.github/workflows/court-sync.yml` | the twice-daily schedule |

Your diary data (hearings, orders, notes) stays in the browser on your device and is
never uploaded. Only the case numbers and party names in `cases.json` are in the repo
— the repo is public, so keep that file to case numbers and names, nothing sensitive.

---

## If something goes wrong

- **Action fails at `pip install pymupdf`** — re-run it; it is a network blip.
- **0 matches, but you know you are listed** — check `caseNo` spelling against the
  list; then check `docs/causelist.txt` and `data.json` to see whether the matter
  was found under a different number (motion lists show `CM-…-CWP-…` with
  `IN CWP-…` underneath).
- **No cause list published yet** — normal in the evening for the next day. The
  06:15 run catches it.
- **Scheduled runs stop after two months** — GitHub disables schedules in repos with
  no activity for 60 days; the sync's own commits count as activity, so this should
  not happen. If it does: Actions → the workflow → *Enable workflow*.
- **Workflow runs are sometimes late** — GitHub's free scheduler can lag by up to
  half an hour at busy times.

---

## Adding another court

`court_sync.py` has one job per court. The shape of a new one:

1. Find how that court serves its cause list for a date (a POST, or a dated PDF URL).
2. Download the PDF and check it has a text layer
   (`python3 -c "import fitz;print(fitz.open('x.pdf')[0].get_text()[:500])"`).
   If it is a scanned image, you need OCR and the job gets heavier.
3. Reuse `parse_pdf()` / `match_entries()`; they are court-agnostic as long as the
   PDF has a serial column, a case-number column and a bench line.
4. Add the court to the workflow as a second step.

District courts (Mohali, Dera Bassi), DRT, consumer commissions and RERA each need
this work. Do one court at a time, and only the ones you appear in weekly.
