# Presentation script, demo, testing and fallbacks (Assignment 5)

## How this builds on Assignment 4 (read this first)

Assignment 4 showed a working prototype. Assignment 5 is the same project, finished. We do **not** start again. The story is: "this is what you saw in Assignment 4, this is what I added, this is the proof that it works, and this is how I fixed every limitation I told you about."

| Assignment 4 | Assignment 5 (this one) |
|---|---|
| One workflow: citizen report to admin triage, CAP and AI | The same workflow, now ending in a verified repair by a contractor |
| Slides: prototype, workflow, UML | Slides: what changed, UML of the final system, live demo, **live testing**, limitations then and now |
| Limitations listed (AI limit, manual scoring, silent model fallback, no button, no citizen email) | Each one is fixed, and each fix is shown with a test |
| Tests described in the report | Tests **run live** on stage |

Marks (50): Q1 intro 6, Q2 live demo 16, Q3 UML 10, Q4 evidence 8, Q5 delivery and questions 10.
The brief asks for 12 to 15 minutes, then about 5 minutes of questions. Ask the lecturer to confirm.

## Before you present (10 minutes before)
1. `bash docs/a5/reset_demo.sh` (backs up the database, then loads the demo data)
2. `bash docs/a5/start_mail_demo.sh` (starts the backend with a mail sink so the audience can see emails)
3. Terminal tab 2: `tail -f ~/Library/Caches/hydrosentinel-dev/mail.log` (emails appear here)
4. Browser: two profiles. Profile A signed in as admin. Profile B ready to sign in as `dlamini-pretorius@contractors.hydrosentinel.co.za` / `contractor123`.
5. Terminal tab 3 at `/Users/malo/Documents/New project/hydrosentinel`, ready to run `bash docs/a5/run_tests_demo.sh`.
6. Slides PDF open on the first slide. Wi-Fi on (for GPT-4o). Fallback videos ready.
7. Optional: `bash docs/a5/start_public.sh` only if the lecturer needs the link. Change the admin password first.

## Timing (target 14:00, limit 15:00). Slide numbers match the deck

| Time | Slide | Say (one idea each) |
|---|---|---|
| 0:00 | 1 to 2 | HydroSentinel closes the loop from a resident's report to a verified repair. Problem, users, aim. |
| 0:45 | 3 | **What changed since Assignment 4.** Say it as a story: contractors, tickets, their own dashboard and AI helpers, citizen email, scoring by itself, the AI limit in the database. Everything in scope is done. |
| 1:45 | 4 | Talk order, the stack, and the emerging technology: XGBoost rates risk, GPT-4o drafts text, a person always decides. |
| 2:00 | 5 to 9 | About 18 seconds each: use case, class, sequence, component, deployment. For the sequence say the six steps and name the AI call. |
| 3:30 | 10 | 55 names checked against the code, 0 mismatches. Three deviations and why. |
| 4:00 | 11 | **Live demo, about 5:30** (script below). |
| 9:30 | 12 | **Testing, live.** Switch to terminal tab 3 and run `bash docs/a5/run_tests_demo.sh` (about one minute). Talk over it: levels (unit, integration, system, user acceptance), 325 and 121 tests, 27 end-to-end checks, UAT 12 of 12. |
| 10:45 | 13 | Measures: 9 ms to list 169 authorities, 89.7% accuracy against 34.5% for the rule. |
| 11:15 | 14 | **Limitations then and now.** Read the five rows. For each one say what I reported in Assignment 4, what I did, and point at the proof. |
| 12:15 | 15 | Privacy and benefit. The citizen's email is optional, never shown, never exported. |
| 12:45 | 16 | The one limit that remains (29 held-out authorities), why it is safe, and the next step. The brief requires one stated limitation. |
| 13:15 | 17 | Contribution, lesson, decision (three sentences each, out loud). |
| 14:00 | 18 | Questions. |

## Demo script (reset first)
| Min | Do | Say | Rubric |
|---|---|---|---|
| 0:00 | Dashboard, click Ekurhuleni | Real audit data for 169 authorities. | 2.1, 2.3 |
| 0:30 | Report form: submit with no description or pin. Add a .txt as a photo. Fix it. Type an email. Submit. | Validation and recovery. I get a reference code. **Watch tab 2: the "we received your report" email appears.** | 2.1 |
| 1:30 | Track by code | Status only: no location, no company. | 2.4 |
| 2:00 | Wrong password, then the right one | Clear error, nothing leaked. | 2.4 |
| 2:20 | Admin: Citizen reports, open the new report, Assign, "Draft with AI", edit, Assign | GPT-4o drafts and suggests. I confirm. The button says Sending, then Sent. | 2.2 |
| 3:15 | Profile B: contractor signs in. Dashboard: tiles, switch Last 7 days to Last 3 months. Click "Summarise my last 30 days". | The contractor sees only its own tickets and its own numbers. The AI only restates the numbers it was given. | 2.2, 2.4 |
| 4:00 | Open the new ticket: "Job brief". Accept. Mark fixed: type a few words, "Help me write it", then Confirm. | The AI drafts and the contractor checks. A fix needs a note. Fixed does not resolve the report. | 2.1, 2.2 |
| 4:45 | Admin: bell, Verify. **Tab 2: the "resolved" email.** | Verify resolves the report. The citizen is told. | 2.1, 2.3 |
| 5:15 | CAP tab: "Score risk now". Then the audit log. | XGBoost level and probability, saved to history, and it also runs by itself every 24 hours. Every step above is in the audit log. | 2.2, 2.4 |

## The testing segment (slide 12), what you run and what to say
`bash docs/a5/run_tests_demo.sh` prints three parts:
1. **End-to-end on the running system**: 27 checks, from a citizen's report to the contractor's ticket being verified, using the real database and GPT-4o. Say: "this is the system test."
2. **The tests for the fixes**: the AI limit, the scheduler, the email over real SMTP, and the contractor AI helpers. Say: "these are the tests that prove the Assignment 4 limitations are gone."
3. **The totals of the full suite** from the saved run: 325 backend, 121 frontend, type check clean. Say: "the full suite takes two minutes, so this is the saved run from today."
Then say the user acceptance result: three testers, four tasks each, 12 of 12 done unaided, average rating 4.25. Be ready to say who the testers were.

## Fallbacks (one sentence, then switch within 15 seconds)
| If | Do |
|---|---|
| OpenAI or Wi-Fi fails | Say "external service unavailable". The template draft and the standard checklist still appear. Show the saved AI output in `evidence/e2e_output.txt`. |
| Emails do not appear | Say the mail sink is local. Show `docs/a5/evidence/pytest_full.txt` (`test_citizen_email.py`). |
| The live test run is slow or fails | Show `docs/a5/evidence/` (`pytest_full.txt`, `e2e_output.txt`) and say it is the same run. |
| Backend stops | `bash docs/a4/start_demo.sh` (10 seconds). If that fails, play the recorded video. |
| Data looks wrong | `bash docs/a5/reset_demo.sh` |
| Projector or laptop trouble | PDF slides and `docs/a5/screens/` on a second device |

**Still to do by you:** record the two fallback videos (full loop about 4 minutes; AI clip about 40 seconds), test playback with Wi-Fi off, run the whole thing three times with a stopwatch.

## Likely questions (answer in two or three sentences, name the file or test)
- **Is this a new project?** No. It is the Assignment 4 system, finished: same workflow, plus contractors and tickets, and every limitation I reported is fixed.
- **How do you know the limitations are fixed?** Slide 14 shows each one with its test. The AI limit is read from the database (`test_ai_rate_limit.py`), scoring runs by itself (`test_scheduler.py`), email goes through real SMTP (`test_citizen_email.py`), and `/health` fails when the model is missing.
- **Why a separate `ReportAssignment` table?** The tracker, CSV and old reports depend on `case_status`. A ticket has its own steps. `models.py`.
- **Why can't a contractor resolve a report?** Fixed is a claim; verifying is the authority's decision. `test_contractor_cannot_skip_steps_or_resolve`.
- **Why 404 and not 403 for another contractor's ticket?** So ids cannot be probed.
- **Two admins assign the same report at once?** A partial unique index allows one open ticket; the loser gets 409.
- **Two servers re-scoring at once?** A database lock lets one work at a time (`test_only_one_server_scores_at_a_time`).
- **What stops the AI inventing things in a fix note?** Every answer is checked: no number and no claim (test, pressure, verified) that the contractor did not write. If it fails a check the contractor gets their own words. `test_contractor_ai.py`.
- **What does the AI change without a person?** Nothing. It drafts; a person assigns, accepts and verifies.
- **What leaves the system to OpenAI?** The ticket facts only, with phone numbers removed. The photo only when an admin presses "Analyse photo". Limited to 20 calls per hour per user.
- **Citizen email privacy?** Optional, never shown, never exported, and the email carries only the code and the status.
- **How good is the model?** 89.7% on 29 held-out authorities, 80.6% cross-validated, 34.5% for the rule. One authority moves it 3.4 points. That is the one limit that remains.
- **Who were the testers and what did they do?** (Use your own answer, and be consistent with the report.)
- **What did you write and what did AI help with?** (Use your declaration wording.)
