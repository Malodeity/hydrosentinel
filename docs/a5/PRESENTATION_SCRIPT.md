# Presentation script, demo and fallbacks (Assignment 5)

Total target 14:00 (limit 15:00). Slide numbers match `slides/slides.html`.

| Time | Slide | Say (one idea) |
|---|---|---|
| 0:00 | 1 to 2 | HydroSentinel closes the loop from a resident's report to a verified repair. Problem, users, aim. |
| 0:45 | 3 | Done: FR-01 to FR-08. Approved change after A4: contractor tickets (FR-12 to FR-18). Not done: FR-09, FR-10, FR-11, photo on fixed. |
| 1:15 | 4 | Talk order. Stack. Emerging tech: XGBoost scores risk, GPT-4o drafts text, a person decides. |
| 1:45 | 5 to 8 | 20 s each on use case, class, component+deployment. Sequence 40 s: walk the 6 steps. Name the AI call. |
| 3:30 | 9 | 60 names checked against the code, 0 mismatches. Three deviations and why. |
| 4:15 | 10 | **Live demo** (about 6:15). |
| 10:30 | 11 to 12 | Tests: 279, 109, 27 of 27, UAT __ of 12. Measures: 7 ms, 89.7% vs 34.5%. |
| 12:00 | 13 to 14 | Privacy by design. Limits and next step. |
| 13:00 | 15 | Contribution, lesson, decision (3 sentences each, out loud). |

## Demo script (reset first: `bash docs/a5/reset_demo.sh`, then `bash docs/a4/start_demo.sh`)

| Min | Do | Say | Rubric |
|---|---|---|---|
| 0:00 | Dashboard, click Ekurhuleni | Real audit data for 169 authorities. NRW is a labelled province estimate. | 2.1, 2.3 |
| 0:40 | Report form: submit with no description or pin; upload a .txt as photo; fix; submit | Validation and recovery. I get a reference code. | 2.1 |
| 1:30 | Track by code | Status only: no location, no company. | 2.4 |
| 2:00 | Sign in with a wrong password, then correct | Clear error, nothing leaked. | 2.4 |
| 2:30 | Admin, Citizen reports, open the new report, Assign to a contractor, "Draft with AI", edit, Assign | GPT-4o drafts and suggests. I confirm. | 2.2 |
| 3:30 | Second browser profile: contractor login, `/tickets`; try `/admin` | Sees only its own tickets. Admin page refuses. | 2.4 |
| 4:00 | Accept, Start, Mark fixed with no note (blocked), then with a note | Validation. Fixed does not resolve. | 2.1 |
| 4:45 | Admin: bell, Verify | Verify resolves the report. Tracker now says resolved. | 2.1, 2.3 |
| 5:30 | CAP tab, pick an authority, "Score risk now" | XGBoost level and probability, saved to history. | 2.2 |
| 6:00 | Audit log | Every step above is there, with who and when. | 2.4 |

## Fallbacks (one sentence, then switch within 15 s)
| If | Do |
|---|---|
| OpenAI or Wi-Fi fails | Say "external service unavailable". The template draft still appears. Then show the saved AI output in `evidence/e2e_output.txt`. |
| Backend stops | `bash docs/a4/start_demo.sh` (10 s). If it fails, play the recorded video. |
| Data looks wrong | `bash docs/a5/reset_demo.sh` |
| Projector or laptop trouble | PDF slides and `docs/a5/screens/` on the second device |

**Still to do by you:** record the two fallback videos (full loop about 4 min; AI clip about 40 s) with Wi-Fi on the real laptop, test playback with Wi-Fi off, run the demo 3 times with a stopwatch.

## Likely questions (answer in 2 to 3 sentences, name the file or test)
- Why a separate `ReportAssignment` table? The tracker, CSV and old reports depend on `case_status`. A ticket has its own steps and history. `models.py`.
- Why can't a contractor resolve a report? Fixed is a claim; verifying is the authority's decision. `test_contractor_cannot_skip_steps_or_resolve`.
- Why 404 and not 403 for another contractor's ticket? So ids cannot be probed. `test_contractor_sees_only_own_tickets_and_cannot_touch_anothers`.
- Two admins assign the same report at once? A partial unique index in PostgreSQL allows one open ticket per report; the loser gets 409. `test_database_refuses_a_second_open_ticket_on_the_same_report`.
- Switch a contractor off while it holds tickets? It keeps them and can finish; no new ones. `test_switched_off_contractor_can_still_finish_tickets_it_already_holds`. The first version locked it out; I found that in review.
- What does the AI change without a person? Nothing. It drafts; a person assigns, accepts, verifies.
- What leaves the system to OpenAI? The report description, and the photo only when an admin presses "Analyse photo". Rate limited to 20 per hour per user.
- How good is the model? 89.7% on 29 held-out authorities, 80.6% cross-validated, 34.5% for the rule. One authority moves it 3.4 points.
- What did you write and what did AI help with? (Use your declaration wording. Be consistent.)
- Demo accounts share a password; is that safe? Seeding is off unless `SEED_DEMO_DATA=true`; users can change their password; admin can reset.
