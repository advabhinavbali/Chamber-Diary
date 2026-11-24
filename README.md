# Court Diary — your chamber app

The app: `index.html`. Your case list for the daily court check: `cases.json`.
The daily check: `court_sync.py` + `.github/workflows/court-sync.yml`.

Everything sits in the top folder of the repository. **There are no folders to
upload** — that is deliberate, because GitHub's upload page skips folders.

Cost: ₹0.

---

## What you get

**In the app (offline, on your device):** case register (case number, CNR, court,
room, parties, stage), hearing diary, to-do list with dates, documents (upload
PDFs and images), orders with read/unread, notes, fee ledger, clients, six-week
schedule, alerts, printable cause list and brief top, CSV and JSON backup.

**Automatically, twice a day:** the Punjab & Haryana High Court cause list is
downloaded and searched for your case numbers. Your matters appear in the app with
court number, item number and bench, and in a calendar feed Google Calendar
subscribes to, with a 9 am reminder the day before.

**Not automatic:** case status, next dates and orders passed — those sit behind a
captcha and a login. You enter the next date from the order; the app keeps the
diary. The sync only tells you what is listed, which is what decides your morning.

---

## Setup, once (about 15 minutes)

You need a free GitHub account and the six files in this zip.

### 1. Upload the six files
On your repository page: **Add file → Upload files**. Drag in these six — they are
plain files, no folders:

    index.html   sw.js   manifest.webmanifest   court_sync.py   cases.json   README.md

Scroll down and press the green **Commit changes**.

### 2. Create the schedule file
This is the only file with a folder in its name, so create it by typing, not uploading.

**Add file → Create new file**. In the file-name box type exactly:

    .github/workflows/court-sync.yml

GitHub will create the two folders by itself. Paste the contents of
`court-sync.yml` from this zip into the big box, then **Commit changes**.

### 3. Your name — the only line you must fill

Open `cases.json` → pencil → set `"advocate"` to your name exactly as it is printed in
the cause list:

```json
{ "advocate": "Abhinav Bali", "cases": [] }
```

That is enough. The sync then finds **every matter where your name appears in the
advocate column** — no case numbers needed, whether you have five cases or five
hundred. Leave `"cases": []` empty; you can add individual cases later, in the app.

Two ways to be found, and you can use both:

| In `cases.json` | What it matches |
|---|---|
| `"advocate": "Abhinav Bali"` | every listing where your name is printed as counsel (badged *by name* in the app — confirm the party) |
| `"cases": [{ "caseNo": "CWP-1234-2024" }]` | one specific case, matched exactly on the case number |

**You never type case numbers by hand.** Add cases in the app as you go
(Cases → + New case), then **Settings → Court sync → Export cases.json** and upload
that file over `cases.json`. If you already have a list in Excel, use
**Settings → Import cases (.csv)** with the CSV template.

### 4. Switch the web page on
**Settings → Pages** → Source: **Deploy from a branch** → Branch **main**,
folder **/ (root)** → **Save**.

Your address is `https://<username>.github.io/<Repository-Name>/`
(for this repository: `https://advabhinavbali.github.io/Chamber-Diary/`).

### 5. Run the court check once
**Actions** → enable workflows if asked → **Court diary sync** → **Run workflow** →
**Run workflow**. Wait two minutes for a green tick. `data.json` and `diary.ics`
appear in the repository.

### 6. Phone
Open your address in **Chrome** → three dots → **Add to Home screen / Install app**.

### 7. Calendar
Google Calendar (on a computer) → **Other calendars +** → **From URL** → paste

    https://<username>.github.io/<Repository-Name>/diary.ics

→ **Add calendar**. Set *Event notifications* on that calendar to "1 day before at
9:00 am" as a backstop.

---

## Daily use

Open the app from the home screen. **Today** shows the day's matters with court and
item number. **To do** shows what is due. After the hearing, tap **Record**, write
one line, put the next date. Upload the order PDF under **Documents**.

---

## Files the sync writes

| File | Meaning |
|---|---|
| `data.json` | your listings: date, CR NO, item, bench, parties |
| `diary.ics` | the calendar feed |
| `causelist.txt` | plain text list to read or forward |

Do not edit those three — they are overwritten twice a day.

---

## If something breaks

- **Folders skipped during upload** — this kit has none. If you see `docs/` or
  `icons/` in an older attempt, delete them; they are not used any more.
- **No green tick in Actions** — run it again; usually a slow download.
- **0 matches** — check `caseNo` spelling, then read `causelist.txt`.
- **App shows no court card** — the sync has not run yet.
- **Uploads (documents) not saving** — open the app from its github.io address, not
  a local file; some browsers restrict storage for local files.

Keep the repository **Public** — Pages and Actions are free on public repositories,
and it holds only case numbers and party names, no hearing notes or documents.
