"""Draws the class diagram picture in the same look as the Assignment 4 one and writes ISJ107V_A5_Q3.2_Class.svg.
Attributes and enumeration values are read from backend/app/models.py and every service operation is imported from the real code, so a wrong
name stops the script. Run from backend/:  PYTHONPATH=. python ../docs/a5/uml/gen_class_picture.py   (build_uml.sh then makes the PNG)"""
import enum, html, importlib, os, sys
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
from app import models
from app.database import Base

HERE = os.path.dirname(os.path.abspath(__file__))
mappers = {m.class_.__name__: m for m in Base.registry.mappers}
SQL = {"UUID": "UUID", "String": "String", "Text": "String", "Float": "Float", "Numeric": "Float", "Integer": "Integer", "Boolean": "Boolean",
       "DateTime": "DateTime", "Date": "Date", "JSONB": "JSON", "JSON": "JSON"}
def attrs(cls, names):
    cols = mappers[cls].columns
    out = []
    for n in names:
        if n not in cols.keys(): sys.exit(f"{cls} has no column {n}")
        t = cols[n].type; ec = getattr(t, "enum_class", None)
        out.append(f"{n} : {ec.__name__ if ec else SQL.get(type(t).__name__, type(t).__name__)}")
    return out
def check_ops(ops):
    for module, fn in ops:
        if not hasattr(importlib.import_module(module), fn): sys.exit(f"{module} has no {fn}")

W, H = 2050, 1830
o = []; a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
a('<defs><marker id="op" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto"><path d="M1,1 L11,6 L1,11" fill="none" stroke="#334155" stroke-width="1.6"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="28" font-weight="700" fill="#0f172a">HydroSentinel: Class Diagram</text>')
LH = 22; B = {}
def box(key, x, y, w, title, at=(), ops=(), stereo=None, fill="#ffffff", head="#e0f2fe", cols=1):
    hh = 52 if stereo else 36
    rows = (len(at) + cols - 1) // cols
    ah = rows * LH + 14 if at else 8
    oh = len(ops) * LH + 14 if ops else 0
    h = hh + ah + oh
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#334155" stroke-width="2"/>')
    a(f'<path d="M{x},{y+hh} V{y+6} Q{x},{y} {x+6},{y} H{x+w-6} Q{x+w},{y} {x+w},{y+6} V{y+hh} Z" fill="{head}" stroke="#334155" stroke-width="2"/>')
    if stereo: a(f'<text x="{x+w/2}" y="{y+19}" text-anchor="middle" font-size="14" font-style="italic" fill="#334155">«{stereo}»</text>')
    a(f'<text x="{x+w/2}" y="{y+hh-11}" text-anchor="middle" font-size="19" font-weight="700" fill="#0f172a">{title}</text>')
    cw = w / cols
    for i, t in enumerate(at):
        c, r = i // rows, i % rows
        a(f'<text x="{x+12+c*cw}" y="{y+hh+20+r*LH}" font-size="14.5" fill="#0f172a">{html.escape(t)}</text>')
    if ops:
        yy = y + hh + ah
        a(f'<line x1="{x}" y1="{yy}" x2="{x+w}" y2="{yy}" stroke="#334155" stroke-width="1.5"/>')
        for i, t in enumerate(ops): a(f'<text x="{x+12}" y="{yy+20+i*LH}" font-size="14.5" fill="#0f172a">{html.escape(t)}</text>')
    B[key] = (x, y, w, h)
def ln(x1, y1, x2, y2, dash=False, mk=False, w=1.9):
    d = ' stroke-dasharray="7 5"' if dash else ""; m = ' marker-end="url(#op)"' if mk else ""
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#334155" stroke-width="{w}"{d}{m}/>')
def poly(pts, dash=False, mk=False, w=1.9):
    d = ' stroke-dasharray="7 5"' if dash else ""; m = ' marker-end="url(#op)"' if mk else ""
    a(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="#334155" stroke-width="{w}"{d}{m}/>')
def t(x, y, s, anchor="middle"):
    bx = x - len(s) * 3.6 - 3 if anchor == "middle" else (x - len(s) * 7.2 - 3 if anchor == "end" else x - 3)
    a(f'<rect x="{bx}" y="{y-12}" width="{len(s)*7.2+6}" height="17" fill="#fff"/><text x="{x}" y="{y}" text-anchor="{anchor}" font-size="13.5" fill="#334155">{html.escape(s)}</text>')
def mult(x, y, s, anchor="start"): a(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="14" font-weight="700" fill="#0f172a">{s}</text>')

DX0, DX1 = 370, 1470
box("user", DX0, 80, DX1 - DX0, "User", attrs("User", ["id", "email", "hashed_password", "role", "is_active", "wsa_id", "contractor_id", "last_login_at", "created_at"]), cols=2, head="#dbeafe")
my = 420
box("hist", DX0, my, 320, "RiskScoreHistory", attrs("RiskScoreHistory", ["id", "risk_level", "probability", "model_source", "model_version", "scored_by", "scored_at"]))
box("rep", DX0 + 360, my, 340, "CitizenReport", attrs("CitizenReport", ["id", "issue_type", "description", "reference_code", "case_status", "admin_comment", "contact_email", "lat", "lng", "photo_analysis", "reviewed_at", "resolved_at", "created_at"]))
box("tic", DX0 + 790, my, DX1 - DX0 - 790, "ReportAssignment", attrs("ReportAssignment", ["id", "status", "instructions", "due_at", "contractor_note", "rejected_reason", "admin_note", "accepted_at", "fixed_at", "closed_at"]))
box("wsa", DX0, 860, 700, "WSA", attrs("WSA", ["id", "name", "province", "blue_drop_score", "nrw_percent", "maint_pct", "cap_status", "cap_due_date", "risk_level", "lat", "lng", "updated_at"]), cols=2, head="#dbeafe")
box("cov", 730, 1140, 270, "ContractorCoverage", attrs("ContractorCoverage", ["id", "issue_types"]))
box("con", 1160, 1140, 310, "Contractor", attrs("Contractor", ["id", "name", "contact_name", "phone", "email", "is_active"]))
RX, RW = 1650, 330
box("rt", RX, 80, RW, "RefreshToken", attrs("RefreshToken", ["token_hash", "expires_at", "revoked_at"]))
box("alert", RX, 650, RW, "Alert", attrs("Alert", ["id", "alert_type", "message", "acknowledged_at", "created_at"]))
S = "#fef3c7"
ALERT_OPS = [("app.alert_helpers", f) for f in ("raise_high_risk_alert", "raise_risk_increased_alert", "raise_report_volume_spike_alert", "raise_geo_cluster_alert", "raise_assignment_overdue_alerts", "resolve_stale_alerts")]
check_ops(ALERT_OPS)
box("alrs", RX, 850, RW, "AlertService", [], ["raise_high_risk_alert(wsa, db)", "raise_risk_increased_alert(...)", "raise_report_volume_spike_alert(..)", "raise_geo_cluster_alert(...)", "raise_assignment_overdue_alerts(db)", "resolve_stale_alerts(db)"], stereo="service", head=S)
box("aud", RX, 250, RW, "AuditLog", attrs("AuditLog", ["id", "action", "table_name", "record_id", "old_value", "new_value", "ip_address", "created_at"]))
check_ops([("app.audit_helpers", "write_audit")]); box("auds", RX, 520, RW, "AuditService", [], ["write_audit(db, user, action,", "    table, record, old, new)"], stereo="service", head=S)
check_ops([("app.assignment_helpers", "can_serve"), ("app.assignment_helpers", "notify"), ("app.assignment_helpers", "public_repair_status")])
box("tr", RX, 1140, RW, "TicketRules", [], ["can_serve(db, contractor, wsa, issue)", "notify(db, users, title, body)", "public_repair_status(ticket)"], stereo="service", head=S)
check_ops([("ai.predict", "predict_wsa_risk"), ("app.routes.risk", "record_score")])
box("rm", 30, 420, 250, "RiskModel", [], ["predict_wsa_risk(wsa)", ": RiskResult", "record_score(wsa, model, db)"], stereo="service", head=S)
check_ops([("app.routes.ai", "call_openai"), ("app.routes.ai", "get_cap_draft"), ("app.routes.ai", "analyze_report_photo"), ("ai.query_agent", "run_query_agent")])
box("ai", 30, 980, 250, "AiService", [], ["call_openai(system, user)", "get_cap_draft(wsa_id)", "analyze_report_photo(id)", "run_query_agent(question)"], stereo="service", head=S)

def X(k): return B[k]
ux, uy, uw, uh = X("user"); ub = uy + uh
for k, nm, m1 in (("hist", "scores", "0..1"), ("rep", "reviews / resolves", "0..1"), ("tic", "assigned by", "0..1")):
    x, y, w, h = X(k); cx = x + w / 2
    ln(cx, ub, cx, y); mult(cx + 8, ub + 18, m1); mult(cx + 8, y - 8, "0..*"); t(cx, (ub + y) / 2 + 5, nm)
wx, wy, ww, wh = X("wsa")
for k, nm in (("hist", "scored over time"), ("rep", "receives")):
    x, y, w, h = X(k); cx = x + w / 2
    ln(cx, y + h, cx, wy); mult(cx + 8, y + h + 18, "0..*"); mult(cx + 8, wy - 8, "1"); t(cx, (y + h + wy) / 2 + 5, nm)
# CitizenReport - ReportAssignment (side by side)
rx_, ry_, rw_, rh_ = X("rep"); tx, ty, tw, th = X("tic")
ln(rx_ + rw_, ry_ + 60, tx, ry_ + 60); mult(tx - 8, ry_ + 52, "0..*", "end"); mult(rx_ + rw_ + 8, ry_ + 52, "1"); t((rx_ + rw_ + tx) / 2, ry_ + 80, "ticket for")
# ReportAssignment - Contractor (straight down the right side of WSA)
cx_, cy_, cw_, ch_ = X("con"); mid = tx + tw / 2
ln(mid, ty + th, mid, cy_); mult(mid + 8, ty + th + 18, "0..*"); mult(mid + 8, cy_ - 8, "1"); t(mid, (ty + th + cy_) / 2 - 70, "worked by")
# ContractorCoverage - WSA and - Contractor
kx, ky, kw, kh = X("cov")
ln(kx + kw / 2, ky, kx + kw / 2, wy + wh); mult(kx + kw / 2 + 8, ky - 8, "0..*"); mult(kx + kw / 2 + 8, wy + wh + 18, "1"); t(kx + kw / 2, (ky + wy + wh) / 2 + 5, "covers")
ln(kx + kw, ky + 45, cx_, ky + 45); mult(kx + kw + 6, ky + 38, "0..*"); mult(cx_ - 6, ky + 38, "1", "end"); t((kx + kw + cx_) / 2, ky + 68, "set up for")
# User -> right column (three exits)
ys = [B["rt"][1] + 28, B["aud"][1] + 28, B["alert"][1] + 28]
e1, e2, e3 = uy + 30, uy + 80, uy + 130
ln(DX1, ys[0], RX, ys[0]); mult(DX1 + 8, ys[0] - 6, "1"); mult(RX - 8, ys[0] - 6, "0..*", "end"); t((DX1 + RX) / 2, ys[0] - 6, "holds")
poly([(DX1, e2), (1600, e2), (1600, ys[1]), (RX, ys[1])]); mult(DX1 + 8, e2 - 6, "0..1"); mult(RX - 8, ys[1] - 6, "0..*", "end"); t(1592, (e2 + ys[1]) / 2 + 4, "performs", "end")
poly([(DX1, e3), (1520, e3), (1520, ys[2]), (RX, ys[2])]); mult(DX1 + 8, e3 - 6, "1"); mult(RX - 8, ys[2] - 6, "0..*", "end"); t(1528, (e3 + ys[2]) / 2 + 4, "acknowledges", "start")
# Alert -> WSA (raised for)
ax_, ay_, aw_, ah_ = X("alert")
poly([(RX, ay_ + 110), (1580, ay_ + 110), (1580, wy + 60), (wx + ww, wy + 60)]); mult(RX - 8, ay_ + 102, "0..*", "end"); mult(wx + ww + 8, wy + 52, "1"); t(1572, (ay_ + 110 + wy + 60) / 2, "raises", "end")
# dependencies
hx, hy, hw, hh_ = X("hist"); mx_, my_, mw_, mh_ = X("rm")
ln(mx_ + mw_, hy + hh_ / 2, hx, hy + hh_ / 2, dash=True, mk=True); t((mx_ + mw_ + hx) / 2, hy + hh_ / 2 - 8, "saves")
poly([(mx_ + mw_ / 2, my_ + mh_), (mx_ + mw_ / 2, wy + 60), (wx, wy + 60)], dash=True, mk=True); t(mx_ + mw_ / 2 + 50, wy + 52, "reads")
bx_, by_, bw_, bh_ = X("ai")
ln(bx_ + bw_, by_ + 40, wx, by_ + 40, dash=True, mk=True); t((bx_ + bw_ + wx) / 2, by_ + 32, "reads")
sx, sy, sw, sh = X("alrs")
ln(sx + sw / 2, sy, sx + sw / 2, ay_ + ah_, dash=True, mk=True); t(sx + sw / 2 + 42, (sy + ay_ + ah_) / 2 + 4, "creates")
dx, dy, dw, dh = X("auds"); lx, ly, lw, lh = X("aud")
ln(dx + dw / 2, dy, dx + dw / 2, ly + lh, dash=True, mk=True); t(dx + dw / 2 + 42, (dy + ly + lh) / 2 + 4, "writes")
rx2, ry2, rw2, rh2 = X("tr")
ln(rx2, ry2 + 45, cx_ + cw_, ry2 + 45, dash=True, mk=True); t((rx2 + cx_ + cw_) / 2, ry2 + 37, "checks")
# enumerations strip
ey = 1440
a(f'<text x="30" y="{ey-14}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">ENUMERATIONS USED BY THE ATTRIBUTES ABOVE</text>')
x = 30
for nm in ("CAPStatus", "RiskLevel", "IssueType", "ModelSource", "AlertType", "AuditAction", "UserRole"):
    cls = getattr(models, nm); assert issubclass(cls, enum.Enum)
    vals = [v.value for v in cls]
    w = max(170, max(len(v) for v in vals) * 8.4 + 28)
    box("e_" + nm, x, ey, w, nm, vals, stereo="enumeration", head="#ede9fe")
    x += w + 16
a("</svg>")
open(os.path.join(HERE, "ISJ107V_A5_Q3.2_Class.svg"), "w").write("\n".join(o))
print("class picture written", W, H)
