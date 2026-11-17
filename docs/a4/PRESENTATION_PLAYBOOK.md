# HydroSentinel: presentation playbook (30 minutes)

Your one-stop plan for the day. Read it end to end twice. Print it or keep it open on a second screen.

Companion files in this folder:
- `QA_PREP.md`: the questions you will be asked, with answers you can say out loud.
- `CODE_GUIDE.md`: how the code fits together, plus a self code-review plan.
- `start_demo.sh`: starts and checks the whole system.
- `ISJ107V_Assignment4_Slides_213355813.pdf`: the slides you present from.

---

## 1. The 30 minutes at a glance

The brief asks for three things: a 5-minute talk (Q5.1), a 10-minute live demo (Q5.2) and technical questions (Q5.4). Everything else is buffer.

| Clock | Minutes | What | Where you are |
|---|---|---|---|
| 0:00 | 1 | Settle in, greet, say who you are and what HydroSentinel is | Slide 1 |
| 0:01 | 5 | **The talk** (12 slides, about 25 seconds each) | Slides 1 to 12 |
| 0:06 | 10 | **Live demo** | Browser, one terminal tab |
| 0:16 | 12 | **Questions** | Slide 12, then the code if asked |
| 0:28 | 2 | Close, thank them, stop | Slide 12 |

**Checkpoints.** Glance at the clock at these moments. If you are behind, drop the item in brackets.
- 0:03, you should be on slide 6 (features). [Speak faster through 4 and 5.]
- 0:06, the talk must be finished. Say "Let me show you" and switch to the browser.
- 0:11, you should be in the admin console. [Skip the Users and Audit tabs.]
- 0:14, you should be showing the CAP draft. [Skip the management report preview.]
- 0:16, stop the demo even if unfinished. Say "I'll leave it there, happy to go deeper in questions."

**The one rule:** finish the demo on time. A clean, complete workflow beats showing more features. The examiners can ask about anything you skip.

---

## 2. Before the day

### The day before
- [ ] Charge the laptop. Bring the charger.
- [ ] Run `bash docs/a4/start_demo.sh` and confirm it prints **READY**.
- [ ] Do one complete dry run of the demo (section 5) against the clock. Time it. Do it twice.
- [ ] Check your OpenAI key is in `.env`, and that AI replies work (submit one test report and see the AI response).
- [ ] Read `QA_PREP.md` out loud. Practise the answers in your own words.
- [ ] Re-read your declaration in the report. You must be able to explain everything the report says.
- [ ] Open the three submitted files and make sure you know what is in them: the report PDF, the slides PDF, and the GitHub repo.
- [ ] Optional but recommended: remove the leftover test reports (see "Cleaning the demo data" below).

### One hour before
- [ ] Arrive early. Test the screen, the cable or the adapter, and the Wi-Fi.
- [ ] Wi-Fi matters: the AI features (summaries, replies, CAP draft) need the internet. Have your phone hotspot ready as a backup.
- [ ] Run `bash docs/a4/start_demo.sh` again. Wait for **READY**.
- [ ] Turn on Do Not Disturb. Close Mail, Slack, Messages and every unused app.
- [ ] Set the browser zoom to 110 to 125% so the back of the room can read it.
- [ ] Open these browser tabs, in this order:
  1. Slides PDF (full screen)
  2. `http://localhost:5173` (dashboard)
  3. `http://localhost:5173/reports` (citizen report page)
  4. `http://localhost:5173/login`
- [ ] Open one terminal tab, in `hydrosentinel/backend`, with this command typed but not run: `python3 scripts/e2e_workflow.py http://localhost:8000` (needs `ADMIN_EMAIL` and `ADMIN_PASSWORD` set, see section 5, step 7).
- [ ] Have a photo ready on the desktop (any image, called `leak.jpg`) for the upload step. Use a REAL photo (a pipe or puddle): the old seeded reports have 1x1-pixel placeholder images, and the AI photo check fails on those (shows "could not be analysed"). Run the photo check only on the report you submit live.
- [ ] Sign in to the admin once in the login tab, then sign out, so you know the credentials work.

### Ten minutes before
- [ ] Reload the slides and press full screen.
- [ ] Take a breath. Read the first slide script one more time.

### Cleaning the demo data (optional)
Your database contains many test reports from development (for example "E2E TEST report" and several leaks in the City of Ekurhuleni). They make the report list noisy and some are very old. If you want a clean list, ask me to prepare a safe cleanup. Do not delete anything by hand five minutes before the session.

---

## 3. Opening (about 60 seconds, then straight to slide 1)

Say, in your own words:

> "Good morning. I'm Malibongwe Mthethwa. My project is HydroSentinel. It's a web application for South Africa's water services. Residents can report a problem, officials can see which municipalities are at risk, and AI helps both sides. I'll talk for about five minutes, then show it working live for about ten, and then I'm happy to take questions."

Do not apologise or say "um, so basically". Start with the title slide still on screen.

---

## 4. The talk: slide by slide (5 minutes)

Each slide has about 25 seconds. The lines below are the *meaning*. Say them naturally; do not read. "If asked" lines are for questions only.

**Slide 1: Title.** *(10 seconds)*
"This is HydroSentinel. Report water problems, see which municipalities are at risk."

**Slide 2: The problem.** *(25 seconds)*
"South Africa audits its municipal water services in long annual PDF reports. Residents have no simple way to report a leak and follow it up. And officials have no single view of which municipalities are at risk and what's being fixed."

**Slide 3: The solution.** *(25 seconds)*
"HydroSentinel closes that loop in three steps. Residents report a problem. Officials act on it. And AI assists by rating each municipality's risk and drafting a plan, but a person always decides." Point at the footnote: "An authority means a Water Service Authority, the body that runs a town's water. We cover 169."

**Slide 4: Architecture.** *(30 seconds)*
"Five parts. The browser is what people use. The server, built in FastAPI, checks logins, applies the rules and keeps a log. The database is PostgreSQL, holding the authorities, reports and alerts. Then two AI components: a risk model and an AI assistant."
*If asked:* React and TypeScript on the front end; Python on the back end.

**Slide 5: Emerging technology.** *(35 seconds)* This is the most important slide for the marks.
"I use two kinds of AI. The risk model is XGBoost. It learned from 144 audited authorities and correctly rated 26 of 29 it had never seen, which is 89.7%. A simple rule of thumb got 10 of 29. The writing assistant is GPT-4o. It replies to residents, drafts a corrective action plan, and answers officials' questions. A person approves before anything changes."
*Define CAP if you have not:* "A Corrective Action Plan is the list of fixes an authority must carry out."

**Slide 6: Prototype features.** *(30 seconds)*
"Eight features work today: the risk map, reporting a problem, tracking a report, triage, alerts, risk rating, an AI action plan, and secure access. One is partial: there's no scoring button in the admin page yet. Two are next: automatic re-scoring and notifying residents."

**Slides 7 to 9: Walkthrough.** *(15 seconds each, 45 total)*
- Slide 7: "A resident gets a reference code and an instant AI reply."
- Slide 8: "An official triages the report, and the system records who did it and when."
- Slide 9: "The AI drafts a plan and a person decides. Nothing changes until someone clicks Accept."
Then say: "Let me show you all of this live." *(Do this at slide 7 if you are running late.)*

**Slide 10: Results.** *(25 seconds)*
"The full workflow passed 17 of 17 automated checks on a fresh install. There are 184 automated tests on the back end and 13 on the front end. Loading all 169 authorities takes about five thousandths of a second."
*Note:* the test counts have grown since the slides were made (see "Numbers" at the end). The slides are not wrong, just conservative. If you want to say the current numbers: 241 back-end tests and 102 front-end tests.

**Slide 11: Limitations.** *(25 seconds)* Be honest and brief. Examiners respect this.
"Three honest limits. The risk model once switched itself off without warning because of a wrong file path. I fixed it so it warns and falls back safely. The AI usage limit lives in one server's memory, so it resets on restart. And risk scoring is started by hand. Each has a clear fix."

**Slide 12: Questions.** *(5 seconds, then switch to the browser)*
"That's the overview. Let me show you it working."

Total: about 5 minutes. Practise with a timer.

---

## 5. The live demo (10 minutes)

**Before you start:** say "I've extended the prototype since I wrote the report, so you'll also see a few improvements. The core workflow is exactly what's in the report." This is honest and prevents confusion.

**Demo credentials:** `admin@hydrosentinel.co.za` / `admin123`

The core idea: follow **one report** from a resident to a resolved case. Use the City of Ekurhuleni (Gauteng).

### Step 1. The dashboard and the AI map summary (0:00 to 0:45)
- Go to the dashboard tab. Point at the **risk map**: green, amber and red circles.
- Say: "Every circle is a municipality, coloured by risk. Clusters group them when zoomed out."
- Click **Summarise this view** (top right of the map). Wait 2 to 3 seconds.
- Say: "AI describes exactly what's on the map: how many authorities, how many are high risk, and the worst ones. Watch, it follows the map." Zoom in once. A moment later the summary updates by itself.
- *If the AI is slow or fails:* "The counts are always live. Only the sentence needs the AI." (The panel still shows counts.)

### Step 2. A resident reports a problem (0:45 to 2:45)
- Go to the **Report Issue** tab.
- Show **validation first** (this is a requirement, Q2.1): point at the greyed-out Submit button. Say: "It stays disabled until a province, an authority and a description of at least 10 characters are in."
- Select **Gauteng**, then **City of Ekurhuleni**, issue type **Leak**.
- Type a description, for example: *"Burst water main on the corner, flooding the road since this morning."*
- Choose a photo (`leak.jpg`). Optionally click the map to move the pin.
- Click **Submit report**.
- Point out: the **reference code** (for example `HS-1A2B3C4D`) and the **AI reply**. Say: "The resident gets a code to follow the case, and a short AI reply that mentions their municipality."
- **Write the code down or copy it.** You need it in step 4.
- Scroll to **Track a report**, paste the code, click **Check status**. It shows *open*.
- Say: "The tracking page shows only the status, never the location or the description. Privacy by design."
- *If the AI reply is missing:* "The report is saved either way; the AI reply is a bonus." That is true: the code handles it.

### Step 3. The official signs in (2:45 to 3:15)
- Go to the login tab. The email is prefilled. Type `admin123`. Click **Sign in**.
- You land on the admin console. Say: "Admin pages are protected. No token, no access: the server returns 401 or 403."
- Point at the six tabs: Overview, Citizen reports, CAP management, AI assistant, Users, Audit log.
- On **Overview**, point at **Reports waiting longest** and the coloured badges. Say: "Reports are flagged by how long they've waited: attention at 3 days, overdue at 7, critical at 14, escalate at 30."

### Step 4. Triage the report (3:15 to 5:00)
- Click **Citizen reports**.
- Paste the reference code into the **search box**. Your report is the only one left.
- Click it. Point at the detail: description, location map, photo count.
- Scroll to **AI photo check** and click **Analyse photo**. After a few seconds it shows what the photo looks like, severity, confidence, and whether it agrees with what the resident reported. Say: "The AI only checks the photo against the report. It can be wrong, so the official still looks. If it disagrees, it flags a mismatch instead of rejecting anything." (Counts as 1 of the 20 AI calls per hour.)
- Open the **Update case status** dropdown and choose **in review**. **Do not save yet.**
- Click **AI comment**. Say: "The AI note follows the status I've selected, so it describes moving the case to review." Read the 1 or 2 sentences it writes.
- Click **Save**. A green message appears at the bottom right.
- Say: "The system records who reviewed it and when." (Point at **Reviewed at**.)

### Step 5. The corrective action plan (5:00 to 7:00)
- Click **CAP management**. Choose province **Gauteng**, type **Ekurhuleni** in the search box, and click the **City of Ekurhuleni** row.
- Point at the **AI risk summary** (it appears after a moment) and the **Risk score history** table. Say: "Each time an authority is scored, we keep the result, including whether it came from the XGBoost model or the fallback rule."
- Click **Draft CAP**. Wait about 3 to 6 seconds.
- Read one item out loud: its priority, deadline and the number it cites.
- Say: "The AI proposes, a person decides." Click **Accept** on one item. The CAP status and due date change.
- Click the **Audit log** tab. Point at the newest rows. Say: "Every change is recorded: who, what, old value, new value. It's append-only."

### Step 6. The AI risk model (7:00 to 8:00)
- Switch to the terminal tab. Run the prepared command:
  `ADMIN_EMAIL=admin@hydrosentinel.co.za ADMIN_PASSWORD=admin123 python3 scripts/e2e_workflow.py http://localhost:8000`
- It takes about 15 seconds and prints PASS lines. Point at **TC-05 XGBoost risk score** and the final **17/17 passed**.
- Say: "This script runs the whole workflow against the live system: report, validation errors, triage, XGBoost scoring, GPT-4o CAP draft, audit. 17 of 17 pass."
- *If the terminal fails:* skip to step 7 and say "Results are in my report, Table 4." (They are.)

### Optional step: the AI assistant tab (60 seconds, only if time allows)
- Before the day, start the back end at least a minute early and ask one regulations question, so the DWS reports are already read (the first question after a restart is slow; later ones are fast).
- Click the **AI assistant** tab. Click one suggested question, for example **Which high-risk authorities have no corrective action plan?**
- Say: "It does not guess. It runs real database queries, and under the answer it lists what it checked." Click **Checked:** to open the detail.
- Point at the meter at the top: "Each AI call counts against an hourly allowance, so cost is controlled."
- Do **not** click every button. Each one is a real OpenAI call.

### Step 7. Close the loop (8:00 to 9:15)
- Back in the admin, set your report to **resolved**, click **Save**.
- Go to the **Report Issue** page and click **Check status** again. It now says **resolved**.
- Say: "The resident sees the outcome."
- Optional (if time): click **Management report** in the admin tab bar. Show page 1. Say: "Officials can export a four-page management report as a PDF: risk by province, how long reports have waited, overdue plans." Do **not** click Download PDF unless you want to show the print dialog.

### Step 8. Wrap the demo (9:15 to 10:00)
Say: "That's the workflow: a resident reports, an official triages, the AI rates risk and drafts a plan, a person approves, and everything is audited. The honest limit is that risk scoring is started by hand today. I'm happy to go deeper in questions."

Switch back to slide 12. **Stop. Wait for the first question.**

---

## 6. Fallback plan (if something breaks)

Stay calm. Say what is happening in plain words, then continue. Examiners mark how you handle problems.

| What breaks | What to say and do |
|---|---|
| **The AI is slow or fails** (no Wi-Fi, OpenAI down) | "The AI features degrade on purpose: the rest of the system keeps working." Show a part that does not need the AI (triage, tracking, audit). Use the screenshots in `docs/a4/screens/` for the AI parts. |
| **The backend is not running** | In a terminal run `bash docs/a4/start_demo.sh` (about 20 seconds). Meanwhile say what the next step would show. |
| **A page is blank or shows an error** | Reload (Cmd+R). If it persists, check `tail ~/Library/Caches/hydrosentinel-dev/backend.log`. |
| **Login fails** | The email is `admin@hydrosentinel.co.za` and the password is `admin123`. If still failing, the backend is probably down: run the start script. |
| **A 429 "AI request limit reached"** | "That's the rate limiter working: 20 AI requests per admin per hour." Move on, or restart the backend to clear it. |
| **Everything fails** | Present from the slides, the report PDF and the screenshots in `docs/a4/screens/`. The sample management report is in `docs/a4/evidence/sample_management_report.pdf`. Walk through `e2e_output.txt` as proof it works. |

**Never** say "it worked yesterday" or blame the laptop. Say what you were about to show and show the evidence instead.

---

## 7. Questions (12 minutes)

Open `QA_PREP.md`. The brief's last criterion (Q5.4) is about answering technical questions and explaining **your own** design, implementation and testing decisions.

How to answer well:
1. **Pause.** Take two seconds. It shows you are thinking, not reciting.
2. **Answer in three parts:** the direct answer (one sentence), why, and the trade-off or limitation. Stop there.
3. **If you do not know:** "I'm not sure of the exact detail. Here's what I do know..." then say what you know. Never invent a number or a detail.
4. **If they ask to see code:** open the file named in `CODE_GUIDE.md`. Do not scroll randomly. Go straight to the function.
5. **Own your choices.** Say "I chose X because Y", not "the AI chose".
6. **Be consistent with your declaration:** you used an AI assistant for code, design and diagrams, integrations, tests and documentation, and you reviewed it and can explain it. If asked directly, say that plainly, then explain the part they point at. That is why the code review in `CODE_GUIDE.md` matters.

---

## 8. Closing (30 seconds)

> "To summarise: HydroSentinel connects residents and officials, uses machine learning to rate risk, and uses a language model to draft actions, with a person approving and every change audited. The prototype passes all its tests and I've been upfront about its limits. Thank you. I'm happy to take any more questions."

Then stop talking.

---

## 9. The numbers you must know cold

| Fact | Value |
|---|---|
| Authorities monitored | 169 |
| Authorities with risk labels for training | 144 |
| Model | XGBoost, 150 trees, depth 4, six inputs |
| Held-out accuracy (29 authorities) | 89.7% (26 of 29) |
| Cross-validated accuracy (5-fold) | 80.6%, plus or minus 8.0 |
| Simple rule-of-thumb accuracy, same 29 | 34.5% (10 of 29) |
| The six model inputs | Blue Drop score, NRW %, maintenance %, CAP status, latitude, longitude |
| Model confidence floor | 50%: below it, the fallback rule is used |
| AI model | GPT-4o, 30 second timeout, one retry |
| AI usage limit | 20 requests per admin per hour (then 429) |
| Database tables | 8 |
| Alert types | 5 (high risk, risk increased, report spike, localized incident, CAP overdue) |
| Spike alert | 5 or more reports in 24 hours for one authority |
| Cluster alert | 3 or more same-issue reports within 2 km in 6 hours |
| Age flags | Attention 3 days, Overdue 7, Critical 14, Escalate 30 |
| Login | Access token (JWT) about 60 minutes; refresh token 7 days, single use |
| Tests (current) | 241 back end, 102 front end, 17 end-to-end checks |
| Tests (in the slides and report) | 184 back end, 13 front end |
| Response time, list of 169 authorities | median 5 ms |
| GPT-4o CAP draft | 2.5 to 5.8 seconds |

---

## 10. If you only remember five things

1. **The story:** residents report, officials act, AI assists, a person decides.
2. **The AI:** XGBoost rates risk (89.7% on unseen data vs 34.5% for a simple rule), GPT-4o writes. Both are used inside the workflow, not bolted on.
3. **The control:** nothing the AI writes changes data until an admin clicks Accept. Everything is audited.
4. **The honesty:** know the three limitations and say them without being asked.
5. **The clock:** finish the demo at 0:16. A calm, complete story wins.
