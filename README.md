# CSE Lecturer Notice Board — self-updating

An auto-refreshing job board for CSE lecturer openings at Bangladeshi private
universities. **Google** crawls the sources, a **GitHub Action** turns your
Google Alerts feed into `notices.json` every 6 hours, and the board
(`index.html`) shows the latest postings live. No Claude, no server, no
maintenance once it's set up.

```
┌─ Google Alerts (crawls Bdjobs, newspapers, LinkedIn, trackers)
│        │  RSS feed
│        ▼
├─ GitHub Action  ──runs feed_to_json.py every 6h──▶  notices.json  (committed)
│        │
│        ▼
└─ index.html (GitHub Pages)  ──reads notices.json──▶  🆕 Latest postings
```

---

## Files

| File | What it does |
|------|--------------|
| `index.html` | The board. Reads `notices.json` and shows a live "Latest postings" strip on top of the curated 27-university baseline. |
| `feed_to_json.py` | Reads your Google Alerts feed(s), filters for relevance, writes `notices.json`. Standard library only. |
| `.github/workflows/refresh.yml` | The scheduled Action (every 6 h + a manual button). |
| `notices.json` | The live data. The Action overwrites it; you don't edit it. |

---

## One-time setup (~10 minutes)

### 1. Create a Google Alert as an RSS feed
1. Go to **https://www.google.com/alerts** (signed in to your Google account).
2. In the box, paste this query:
   ```
   lecturer (CSE OR "computer science") Bangladesh
   ```
3. Click **Show options** → set **Deliver to** = **RSS feed** → **Create Alert**.
4. On the alerts list, an **RSS icon** ( 🔖 ) appears next to your alert.
   **Right-click it → Copy link address.** That long URL is your feed URL —
   keep it handy for step 3. *(Optional: make a second alert, e.g.
   `"assistant professor" CSE Bangladesh`, and copy its feed too.)*

### 2. Create the GitHub repo
1. New **public** repo (public = free GitHub Pages), e.g. `cse-lecturer-board`.
2. Upload all files from this folder, keeping the `.github/workflows/` path
   intact. *(GitHub web UI: "Add file → Upload files", then drag everything in.
   To create the nested folder, type `.github/workflows/refresh.yml` as the file
   name when adding it, or upload the folder directly.)*

### 3. Add your feed URL as a secret
1. Repo **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: `FEED_URLS`  ·  Value: your feed URL from step 1
   (paste several comma-separated if you made more than one).
   *Using a secret keeps your feed URL out of the public repo.*

### 4. Allow the Action to commit
- **Settings → Actions → General → Workflow permissions** →
  select **Read and write permissions** → **Save**.
  *(Without this the Action can't push the updated `notices.json`.)*

### 5. Turn on GitHub Pages
- **Settings → Pages → Build and deployment → Source = Deploy from a branch**
  → Branch **main** / **/(root)** → **Save**.
  Your board goes live at `https://<your-username>.github.io/cse-lecturer-board/`.

### 6. Run it once
- **Actions** tab → **Refresh notices** → **Run workflow**.
  After ~30 s it commits `notices.json`; Pages redeploys; open your Pages URL
  and the **🆕 Latest postings** strip appears. From here it refreshes itself
  every 6 hours.

---

## Tweaks

- **Refresh rate:** edit the `cron` in `refresh.yml` (`0 */6 * * *` = every 6 h;
  `0 */2 * * *` = every 2 h).
- **What counts as relevant:** edit `ROLE` / `JOB_INTENT` / `FIELD` in `feed_to_json.py`
  (a role word alone passes; a field mention needs a job-intent word alongside it).
- **Run locally to test:** `FEED_URLS="<your-feed-url>" python feed_to_json.py`
  (Windows PowerShell: `$env:FEED_URLS="<url>"; python feed_to_json.py`).

## Honest limits

- The live strip shows **headlines** (title, source, date, link) — not perfectly
  parsed "open/closed/deadline" states. Deadlines are a best-effort guess and are
  often blank; always open the linked circular to confirm.
- Coverage = whatever your Google Alert catches. Broaden the query or add feeds
  to widen it.
- The curated 27-university cards, salary tiers, and process notes in the board
  are the hand-checked baseline (updated 24 Jul 2026); they don't auto-update.
