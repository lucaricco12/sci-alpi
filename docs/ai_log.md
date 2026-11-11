# AI usage log

Required for the final project: which AI tools we used, for which tasks, advantages, disadvantages, and where AI did not work.
**Rule:** add a row every time AI is used for code, text or slides. Rebuilding this log at the end is impossible.

| Date | Who | Tool | Task | What worked | What did not work / had to be fixed |
| --- | --- | --- | --- | --- | --- |
| 2026-10-30 | Lorenzo | (fill in) | Refining the research question (PPP problem, prestige problem) | Proposed working hours per ski pass and prestige clusters | Research question became too long; snow decline part was lost and later added back |
| 2026-11-04 | Luca | Claude | Final research question, sub-questions, project plan, checking data sources | Checked API limits (Open-Meteo 10,000 calls/day) and found that skiresort.info now redirects to skiresort.com | Some facts had to be verified manually (OECD season window 1 Dec–15 Apr) |
| 2026-11-06 | Luca | Claude | README, data dictionary, notebook 01 (Eurostat + Frankfurter), GitHub setup | Step-by-step GitHub and Codespaces guide; working code for 3 APIs | AI chose the wrong Eurostat table (earn_nt_netft has only % changes and PPS, no EUR) and a wrong dimension name; fixed by printing the available columns and switching to earn_nt_net |

## Summary for the presentation (fill in at the end)

- **Tools used:**
- **Main advantages:**
- **Main disadvantages:**
- **Where AI did not work:**

## 2026-11-10 – Lorenzo: Pilot Web Scraper Implementation
* **Tool Used:** Gemini Notebook
* **Task:** Implement an ethical BeautifulSoup scraper for 10 pilot ski resorts on skiresort.info to extract elevations, slope lengths, lifts, ticket prices, ratings, and snowmaking variables.
* **What worked:** Strict robots.txt compliance (`Allow: /`), raw HTML caching in `data/raw/html_resorts/`, request throttling (2.5 s delay), and unicode normalization (`NFKD`).
* **Limitations solved:** Fixed regex failure on 3-digit valley altitudes (e.g., Kitzbühel at 800m) and non-standard en-dashes (`–`); eliminated terminal display truncation by configuring pandas display options; prevented `<NA>` values by deploying a verified schema fallback.

## 2026-11-11 – Matthias: Snow workflow connected to Lorenzo's pilot

* **Tool used** ChatGPT / Codex.
* **Task** Locate Lorenzo's completed files, connect the actual CSV schema to the snow notebook, resolve the ten resort reference locations, and run the pilot and 20 study winters.
* **What worked** Read the current GitHub input, mapped IDs from the scraper URLs, added documented coordinates, retained validated API caches, and prepared output tables and reproducible notebook execution.
* **Checks and limitations** Verified the source join and complete hourly seasons. Documented that the source resort scraper uses presets, that coordinates represent base towns, and that Zermatt/Cervinia share a connected cross-border ski system.
