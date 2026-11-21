"""Draws the component diagram in the same look as the class and use-case diagrams and writes ISJ107V_A5_Q3.4a_Component.svg.
Every line is straight or has right angles and none crosses another. ISJ107V_A5_Q3.4a_Component.puml holds the same components as editable text.
Run: python3 gen_component.py   (build_uml.sh then makes the PNG)"""
import html, os
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1900, 1040
o = []; a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
a('<defs><marker id="op" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto"><path d="M1,1 L11,6 L1,11" fill="none" stroke="#334155" stroke-width="1.6"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="28" font-weight="700" fill="#0f172a">HydroSentinel: Component Diagram</text>')

def band(x, y, w, h, label, col):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{col}" opacity="0.55"/>')
    a(f'<text x="{x+18}" y="{y+26}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">{html.escape(label)}</text>')
def comp(x, y, w, h, title, lines=(), cols=1, head="#e0f2fe"):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fff" stroke="#334155" stroke-width="2"/>')
    a(f'<path d="M{x},{y+36} V{y+6} Q{x},{y} {x+6},{y} H{x+w-6} Q{x+w},{y} {x+w},{y+6} V{y+36} Z" fill="{head}" stroke="#334155" stroke-width="2"/>')
    ix, iy = x + w - 34, y + 10    # the UML component symbol
    a(f'<rect x="{ix}" y="{iy}" width="20" height="16" fill="#fff" stroke="#334155" stroke-width="1.5"/><rect x="{ix-5}" y="{iy+3}" width="10" height="4" fill="#fff" stroke="#334155" stroke-width="1.3"/><rect x="{ix-5}" y="{iy+9}" width="10" height="4" fill="#fff" stroke="#334155" stroke-width="1.3"/>')
    a(f'<text x="{x+w/2-8}" y="{y+25}" text-anchor="middle" font-size="18" font-weight="700" fill="#0f172a">{html.escape(title)}</text>')
    rows = (len(lines) + cols - 1) // cols
    for i, t in enumerate(lines):
        c, r = i // rows, i % rows
        a(f'<text x="{x+16+c*(w-20)/cols}" y="{y+62+r*23}" font-size="14.5" fill="#0f172a">{html.escape(t)}</text>')
def ln(pts, dash=False, mk=True):
    d = ' stroke-dasharray="7 5"' if dash else ""; m = ' marker-end="url(#op)"' if mk else ""
    a(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="#334155" stroke-width="1.9"{d}{m}/>')
def label(x, y, s, anchor="middle"):
    bx = x - len(s) * 3.7 - 4 if anchor == "middle" else (x - len(s) * 7.4 - 4 if anchor == "end" else x - 4)
    a(f'<rect x="{bx}" y="{y-13}" width="{len(s)*7.4+8}" height="19" fill="#fff"/><text x="{x}" y="{y}" text-anchor="{anchor}" font-size="13.5" fill="#334155">{html.escape(s)}</text>')
def cloud(cx, cy, text, w=230, h=84):
    a(f'<ellipse cx="{cx}" cy="{cy}" rx="{w/2}" ry="{h/2}" fill="#f1f5f9" stroke="#334155" stroke-width="2"/>')
    parts = text.split("\n")
    for i, t in enumerate(parts): a(f'<text x="{cx}" y="{cy+5+(i-(len(parts)-1)/2)*20}" text-anchor="middle" font-size="16" fill="#0f172a">{html.escape(t)}</text>')

# ---- bands
band(330, 70, 1200, 150, "FRONT END (React 18, Vite, Tailwind)", "#e0f2fe")
band(330, 240, 1200, 510, "BACK END (FastAPI)", "#fef3c7")
band(330, 770, 1200, 245, "DATA", "#fce7f3")
# ---- front end
comp(380, 104, 480, 100, "Pages", ["DashboardPage, ReportPage, AdminPage,", "ContractorTicketsPage, NotificationBell"])
comp(1000, 104, 420, 100, "api/client.ts", ["axios client: attaches the JWT,", "refreshes it on 401"])
ln([(860, 154), (1000, 154)])
# ---- routers
comp(380, 275, 1100, 150, "Routers (one file per area)", ["routes/reports.py", "routes/assignments.py", "routes/risk.py", "routes/ai.py", "routes/contractor_ai.py", "routes/auth.py", "routes/wsa.py", "routes/alerts.py", "routes/audit.py", "routes/users.py"], cols=3)
ln([(1210, 204), (1210, 275)]); label(1210, 244, "HTTP/JSON, Bearer JWT", "start")
# ---- services and AI
comp(380, 520, 450, 190, "Services", ["app/auth.py", "app/assignment_helpers.py", "app/alert_helpers.py", "app/audit_helpers.py", "app/rate_limit.py", "app/mailer.py", "app/scheduler.py"], cols=2)
comp(1060, 520, 420, 190, "AI modules", ["ai/predict.py (XGBoost + heuristic)", "ai/rag.py (regulatory PDFs)", "ai/query_agent.py"])
ln([(560, 425), (560, 520)]); label(560, 478, "use", "end")
ln([(660, 520), (660, 425)], dash=True); label(672, 478, "scheduler calls record_score", "start")
ln([(1270, 425), (1270, 520)]); label(1282, 478, "predict, retrieve, ask", "start")
# ---- data
comp(830, 800, 230, 80, "app/models.py", ["SQLAlchemy models"], head="#fce7f3")
comp(1085, 800, 195, 80, "ai/model.pkl", ["XGBoost"], head="#fce7f3")
comp(1300, 800, 210, 80, "data/uploads", ["photos"], head="#fce7f3")
a(f'<ellipse cx="945" cy="935" rx="95" ry="14" fill="#fff" stroke="#334155" stroke-width="2"/><path d="M850,935 V978 A95,14 0 0 0 1040,978 V935" fill="#fff" stroke="#334155" stroke-width="2"/><text x="945" y="970" text-anchor="middle" font-size="17" font-weight="700" fill="#0f172a">PostgreSQL</text>')
ln([(945, 425), (945, 800)]); label(957, 620, "read and write", "start")   # runs in the gap between Services and AI
ln([(615, 710), (615, 840), (830, 840)]); label(720, 832, "use", "middle")
ln([(945, 880), (945, 921)]); label(957, 905, "SQLAlchemy", "start")
ln([(1175, 710), (1175, 800)]); label(1187, 760, "load at startup", "start")
# ---- external services
cloud(165, 615, "SMTP server\n(optional)")
ln([(380, 615), (282, 615)]); label(165, 690, "only if SMTP_HOST is set", "middle")
cloud(1730, 300, "OpenAI API (GPT-4o)\nkey from .env")
ln([(1480, 300), (1615, 300)]); label(1548, 286, "HTTPS", "middle")
ln([(1480, 395), (1580, 395), (1580, 840), (1510, 840)]); label(1592, 600, "photos", "start")
a("</svg>")
open(os.path.join(HERE, "ISJ107V_A5_Q3.4a_Component.svg"), "w").write("\n".join(o))
print("component picture written", W, H)
