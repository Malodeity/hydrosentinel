# Terms in plain words (for you, not for the slides)

How Assignment 4 did it: the slide **footers** explained the terms on the slide (WSA, CAP), `a4/PRESENTATION_SCRIPT.md` section A2 had "the words, in 30 seconds", and `a4/CODE_GUIDE.md` section 9 had the glossary. For Assignment 5 it is the same idea:
- every slide footer in the deck explains its own terms,
- slide 21 (backup) lists the main ones,
- **this file** is the full list with a line you can say out loud. Read it before you present. It is not part of the slides.

## The three you say first (30 seconds)
1. **WSA, Water Service Authority.** "The municipality legally responsible for a town's water. It is the unit we monitor. We track 169."
2. **Blue Drop score.** "The Department of Water and Sanitation's drinking-water rating from 0 to 100. Higher is better. 95 and above is certified."
3. **CAP, Corrective Action Plan.** "When an authority fails, it must say what it will fix and by when. We track that promise. Overdue means the deadline passed and the plan is not complete."

## The water world
| Term | Plain meaning | Say it like this |
|---|---|---|
| WSA | Water Service Authority: the municipal body that runs a town's water | "The authority we monitor. 169 of them." |
| DWS | Department of Water and Sanitation, the national department that audits the authorities | "The government department that publishes the audits." |
| Blue Drop | DWS score for drinking-water quality, 0 to 100 | "Higher is better. Under 31 is critical." |
| Green Drop | DWS score for wastewater management | "The sewage-treatment equivalent of Blue Drop." |
| No Drop | DWS report on water losses | "How much water an authority loses." |
| NRW | Non-revenue water: water lost before it can be billed | "Leaks and theft. It is a labelled province estimate in our data." |
| BDRR | Blue Drop Risk Rating, the DWS risk label | "It is the label I trained the model on." |
| CAP | Corrective Action Plan | "The authority's promise of what it will fix, and by when." |
| Risk level | Low, medium or high, set by the model | "The output of the AI: it colours the map." |
| Reference code | The code a citizen gets after reporting (like HS-1A2B3C4D) | "The citizen's receipt. It shows status only." |

## The people and the workflow
| Term | Plain meaning | Say it like this |
|---|---|---|
| Citizen | Anyone who reports a problem. No account needed | "No account, just a report." |
| Admin (national) | Staff who see every authority | "Triage, CAP, scoring, users." |
| Authority admin | An admin limited to one authority | "They can only see their own authority." |
| Contractor | A repair company with its own login | "Sees only its own tickets." |
| Ticket | One repair job given to a contractor for a report | "A report becomes a ticket with an owner and a due time." |
| Verify | The authority checks the work and closes the ticket | "Only the authority can resolve a report, never the contractor." |
| Send back | The authority says the work is not good enough | "The contractor fixes it again." |
| Coverage | The authorities and issue types a contractor is set up for | "A contractor only gets reports it is set up to serve." |
| Triage | Looking at a new report and deciding what to do | "Open, in review, resolved." |

## The technology (stack)
| Term | Plain meaning | Say it like this |
|---|---|---|
| React, Vite, Tailwind | The tools the screens are built with | "The front end." |
| FastAPI | The Python server | "The back end." |
| PostgreSQL | The database | "Where everything is stored." |
| API | How the screens talk to the server | "The server's menu of requests." |
| Router | The code that answers one kind of request | "One file per area." |
| ORM / SQLAlchemy | Lets code use database tables as classes. It also prevents SQL injection | "Queries are parameterised." |
| JWT | The signed token that proves who is signed in | "Short-lived, with a refresh token behind it." |
| Refresh token | A longer-lived token that gets a new JWT. Stored only as a hash | "Single use: it is replaced each time." |
| bcrypt | A deliberately slow way to hash passwords | "Passwords are never stored in plain text." |
| SMTP | The standard way email is sent | "It works with any mail provider." |
| STARTTLS | Encrypts the connection to the mail server | "Used whenever the server offers it." |
| Background task | Work done after the response, such as sending an email | "A slow mail server never delays a citizen." |
| Advisory lock | A database lock so only one server does a job at a time | "Two servers never re-score at once." |
| Health check | A page that fails when something needed is missing | "It returns 503 if the risk model is not loaded." |
| ngrok | A tool that gives a local app a public web address | "Only for letting someone else try it." |

## The AI
| Term | Plain meaning | Say it like this |
|---|---|---|
| XGBoost | The machine-learning model that rates risk | "Trained on 144 audited authorities." |
| GPT-4o | OpenAI's language model that writes text | "It drafts. A person decides." |
| TF-IDF | A way of finding the page that matches a question by its words | "How the regulations question box finds the right passage." |
| Accuracy | The share of authorities the model rated correctly | "89.7% on 29 it had never seen." |
| Held-out set | Authorities kept back to test the model | "26 of 29 correct." |
| Cross-validation | Testing on several different splits of the data | "80.6%. One authority moves the 89.7% by 3.4 points." |
| Rule baseline | A simple rule of thumb to compare against | "34.5%, so the model clearly helps." |
| Fallback | What the system does when the AI is not available | "A plain rule or a template. Never an error." |
| Answer checks | Checks on every AI answer before it is shown | "No invented number, no invented claim, no link." |
| Prompt injection | Text inside data that tries to give the AI orders | "It is passed as data and the AI is told to ignore orders in it." |

## Testing words
| Term | Plain meaning | Say it like this |
|---|---|---|
| Unit test | Tests one small function | "Fast and precise." |
| Integration test | Tests parts working together, such as the database and the API | "pytest on the real database." |
| System test / end-to-end | Tests the whole workflow on the running system | "27 checks, from the report to the verified repair." |
| UAT | User acceptance testing with real people | "3 testers, 4 tasks each, 12 of 12." |
| TC | Test case, with an ID such as TC-05 | "The numbers in the evidence table." |
| pytest / Vitest | The test tools for the back end and the front end | "325 and 121 tests." |
| Rollback | Each test undoes its changes, so real data is never touched | "Tests run in transactions that roll back." |
| Median | The middle response time | "9 ms to list 169 authorities." |
| p95 | 95 of 100 calls were faster than this | "13 ms." |

## Requirements words
| Term | Plain meaning |
|---|---|
| FR | Functional requirement: what the system does (FR-01 to FR-23, all completed) |
| NFR | Non-functional requirement: how well it does it (speed, security, privacy, reliability, integrity) |
| ETR | Emerging-technology requirement: the AI parts (ETR-01 to ETR-03) |
| UML | Standard diagrams of a system's design |
| Actor | A person or system that uses the system |
| Include / extend | Include: a function that always needs another first. Extend: an optional step added to a function |

## Error codes (you may be asked)
| Code | Meaning | Where we use it |
|---|---|---|
| 401 | Not signed in | Admin list with no token |
| 403 | Signed in but not allowed | A contractor calling an admin route |
| 404 | Not found | Another contractor's ticket (so ids cannot be probed) |
| 409 | Conflict | Second admin assigning the same report; a step out of order |
| 422 | Invalid input | Wrong issue type; fix without a note; a bad email |
| 429 | Too many requests | The AI limit of 20 per hour |
| 502 / 503 | OpenAI failed / not configured, or health check failed | Fallback text for the user; 503 on `/health` |
