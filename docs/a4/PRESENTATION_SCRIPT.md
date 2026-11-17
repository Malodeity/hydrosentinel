# What you present: Question 5, mapped to the rubric

Source: Assignment 4 brief, Question 5 (10 marks). Everything below is built so each mark has something you can point to.

| Item | Marks | What the brief asks | Where you earn it |
|---|---|---|---|
| 5.1 | 3 | 5-minute structured talk: problem, solution, architecture, emerging technology, features, results, limitations | The talk (section A) |
| 5.2 | 4 | 10-minute live demo of the main workflow and the AI integration, with sample data and a fallback plan | The demo (section B) and the fallback table in `PRESENTATION_PLAYBOOK.md` |
| 5.3 | 1 | Readable slides, professional, on time | Slides plus a clock check at 0:03 |
| 5.4 | 2 | Answer technical questions and explain your own design, build and testing decisions | Q&A (section C), `QA_PREP.md` |

Rubric top band (9 to 10): focused and professional, convincing live demo, technical answers that show strong individual understanding. The "individual understanding" part is why section C matters as much as the talk.

---

## A. The 5-minute talk (about 750 spoken words)

The brief lists seven topics. Spend time in proportion to what the markers can award marks for.

| Time | Topic (brief wording) | Slide | Say, in this order |
|---|---|---|---|
| 0:00 | Title | Intro 1 | Name, module, one sentence: "Report water problems, see which municipalities are at risk." |
| 0:10 | **Problem** | Intro 2 | PDFs nobody can compare. Residents cannot report and follow up. Officials have no single view. 169 authorities. |
| 0:40 | **The words you need** | Intro 4, 5 (cut to the three terms below) | See section A2. This is the part that makes everything after it make sense. |
| 1:10 | **Proposed solution** | Intro 3 | Resident reports, official acts, AI assists, public sees. Rule: a person always decides. |
| 1:40 | **Architecture** | Deck slide 4 | Browser, FastAPI server, PostgreSQL, XGBoost model, GPT-4o. One sentence each. |
| 2:10 | **Emerging technology** | Deck slide 5 | The most important slide. Two kinds of AI, with numbers (A3). |
| 3:10 | **Prototype features** | Deck slide 6 | Four tiles: report, triage, CAP, alerts. Then "let me show you." |
| 3:40 | **Results** | Deck slide 10 | Accuracy, tests, response time. |
| 4:15 | **Limitations** | Deck slide 11 | Two honest limits and the fix for each. |
| 4:45 | Hand-over | Deck slide 12 | "I will now show it running." Switch to the browser. |

If you are behind at 0:03 you should be on the emerging-technology slide. Drop the "words" slide to ten seconds, never the emerging-technology slide.

### A1. Why the intro visual does not fit whole
The visual has seven slides. In 5 minutes you can show **3 of them live**: slides 2, 3 and 6 (Problem, Solution, CAP). Keep slides 4 and 5 (Who is who, How an authority is graded) as backup for questions, because a marker may ask "what is a Blue Drop score?". Slide 7 (how the terms connect) is a good answer to "walk me through the system".

### A2. The words, in 30 seconds
Say these three, in this order, and do not read the slide.
1. **WSA, Water Service Authority.** "The municipality legally responsible for a town's water. It is the unit we monitor. We track 169."
2. **Blue Drop score.** "The Department of Water and Sanitation's drinking-water rating from 0 to 100. Higher is better. 95 and above is certified."
3. **CAP, Corrective Action Plan.** "When an authority fails, it must say what it will fix and by when. We track that promise. Overdue means the deadline passed and the plan is not complete."

Say "risk level" once as the output: low, medium or high, set by the AI model.

### A3. The emerging-technology slide (35 to 60 seconds, the marks live here)
- **Risk model, XGBoost.** Trained on 144 audited authorities. On 29 it had never seen it rated 26 correctly, 89.7%. A simple rule of thumb got 10 of 29 (34.5%). Cross-validation 80.6%. Say the cross-validation number yourself so nobody has to catch it: 29 authorities means one wrong answer moves accuracy by about 3.4 points.
- **Inputs:** Blue Drop score, water-loss percentage (NRW), maintenance spending share, CAP status, location.
- **Writing assistant, GPT-4o.** Acknowledges residents, drafts CAP items, answers officials' questions from the database with read-only tools. A person accepts before anything changes.
- **Used by the system, not decoration** (rubric 2.2): the model's output sets the risk level, the map colour and the alerts. An accepted CAP item changes real data.

---

## B. The 10-minute live demo (5.2, 4 marks)
Follow the steps already written in `PRESENTATION_PLAYBOOK.md` section 5. The order below is the order that proves the rubric words "main workflow and emerging-technology integration":

1. Public dashboard and AI map summary (0:45). Shows real data and the AI.
2. A resident reports a problem (2 min). Shows validation (Submit disabled until valid), photo, reference code, instant AI reply.
3. Admin signs in (30 s). Shows access control.
4. Triage the report (1:45). Status changes and the audit log records who and when.
5. **CAP** (2 min). Put slide 6 of the intro visual on screen first for 10 seconds, then switch. Draft with AI, read one justification aloud, click Accept, show status and deadline change.
6. Risk model (1 min). Score an authority and say the source: XGBoost or heuristic.
7. Close the loop (1:15) and wrap.

Say once, out loud: "The data is real: 169 authorities from DWS reports and National Treasury."

Fallback (required by the brief): if anything breaks, move to screenshots in `docs/a4/screens/` and `evidence/e2e_output.txt`. Say "I recorded this earlier" so it reads as planned.

---

## C. Questions (5.4, 2 marks): what they will ask and where the answer is
The rubric rewards explaining **your own decisions**. Prepare these four in your own words.

| Likely question | One-line answer | Backup |
|---|---|---|
| Why XGBoost and not a simpler model? | Small tabular data, handles missing values, and it beat the rule of thumb 89.7% to 34.5% on held-out data. | `QA_PREP.md` |
| What if the AI is wrong or the model is missing? | The model is only used above 50% confidence, otherwise a rule-based fallback scores it. GPT-4o output is never applied until a person clicks Accept. | `predict.py` |
| How is it secured? | JWT logins with refresh tokens, admin-only routes, hashed passwords and refresh tokens, per-admin AI limit of 20 an hour, audit log. | report 2.4 |
| What are the limits? | The 20-per-hour counter lives in one process, scoring runs on request not on a schedule, and accuracy rests on 29 test cases. | slide 11 |

Also be ready to say who wrote what. The declaration says AI assisted with code, design, diagrams, tests and documentation. Be able to explain any file you open, `CODE_GUIDE.md` shows where each feature lives.

---

## D. Slides vs this plan
- Keep the 12-slide deck as the submitted file (Brightspace). Use the intro visual as the **opening and backup**, not a second deck.
- Test counts: the deck still says 184 back-end and 13 front-end tests. Current numbers are 241 and 102. Update the deck or say the new numbers aloud.
- Rehearse once with a timer. The common failure is the talk running to 7 minutes and eating the demo.
