"""Draws the use-case diagram (same look as the Assignment 4 one) and writes ISJ107V_A5_Q3.1_UseCase.svg.
Run:  python3 gen_usecase.py   then render the PNG with headless Chrome (see build_uml.sh)."""
import html, math, os
HERE = os.path.dirname(os.path.abspath(__file__))

PUBLIC = [("map", ["View risk map and", "AI summaries"]), ("sub", ["Submit report", "with photos"]), ("trk", ["Track report by", "reference code"]), ("eml", ["Get email updates", "(if asked for)"])]
SIGNED = [("work", ["Work my tickets", "(accept, reject, start, fix)"]), ("rph", ["Add repair photos"]), ("brf2", ["Get AI job brief"]), ("fxn", ["Write fix note with AI"]), ("dsh", ["View my dashboard", "and AI summary"])]
ADMIN = [("tri", ["Triage report"]), ("note", ["Draft AI case note"]), ("asg", ["Assign report to contractor"]), ("tkt", ["Draft ticket with AI"]),
         ("ver", ["Verify or send back repair"]), ("scr", ["Score WSA risk (XGBoost)"]), ("cap", ["Update CAP status and deadline"]),
         ("dft", ["Draft CAP with AI"]), ("acc", ["Accept CAP item"]), ("con", ["Manage contractors"]), ("ask", ["Ask AI about data or regulations"]),
         ("alr", ["Review and acknowledge alerts"]), ("aud", ["View audit log"]), ("usr", ["Manage admin users"])]
GPT = ("map", "sub", "note", "tkt", "dft", "ask", "brf2", "fxn", "dsh")
EXTENDS = (("note", "tri"), ("tkt", "asg"), ("acc", "dft"), ("rph", "work"))

W = 1700
BX, BW = 340, 1060
UCW, UCH, UX = 400, 54, 610
STEP = 64
o = []; a = o.append

# ---- layout: three bands, top to bottom
BY = 80
y_pub = 120; pub_h = 420
y_sig = y_pub + pub_h + 20; sig_h = 50 + len(SIGNED) * STEP + 14
y_adm = y_sig + sig_h + 20; adm_h = 50 + len(ADMIN) * STEP + 14
BH = y_adm + adm_h + 20 - BY
H = BY + BH + 40
pos = {}
for i, (k, _) in enumerate(PUBLIC): pos[k] = (UX, 210 + i * 90)
for i, (k, _) in enumerate(SIGNED): pos[k] = (UX, y_sig + 58 + i * STEP)
for i, (k, _) in enumerate(ADMIN): pos[k] = (UX, y_adm + 58 + i * STEP)

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
a('<defs><marker id="op" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto"><path d="M1,1 L11,6 L1,11" fill="none" stroke="#334155" stroke-width="1.6"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="28" font-weight="700" fill="#0f172a">HydroSentinel: Use-Case Diagram (final system)</text>')
a(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="14" fill="#f8fafc" stroke="#475569" stroke-width="2.2"/>')
a(f'<text x="{BX+BW/2}" y="{BY+34}" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">HydroSentinel</text>')

def band(y, h, label, col):
    a(f'<rect x="{BX+14}" y="{y}" width="{BW-28}" height="{h}" rx="10" fill="{col}" opacity="0.55"/>')
    a(f'<text x="{BX+30}" y="{y+24}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">{label}</text>')
band(y_pub, pub_h, "PUBLIC FUNCTIONS (NO SIGN-IN)", "#e0f2fe")
band(y_sig, sig_h, "CONTRACTOR FUNCTIONS (SIGN-IN REQUIRED)", "#dcfce7")
band(y_adm, adm_h, "ADMIN FUNCTIONS (SIGN-IN REQUIRED)", "#fef3c7")

def uc(cx, cy, lines):
    a(f'<ellipse cx="{cx}" cy="{cy}" rx="{UCW/2}" ry="{UCH/2}" fill="#fff" stroke="#334155" stroke-width="2"/>')
    n = len(lines)
    for i, l in enumerate(lines):
        a(f'<text x="{cx}" y="{cy+5+(i-(n-1)/2)*19}" text-anchor="middle" font-size="16.5" fill="#0f172a">{html.escape(l)}</text>')

def line(x1, y1, x2, y2, col="#334155", dash=None, mk=False, w=1.8):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#op)"' if mk else ""
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d}{m}/>')

def actor(x, y, name, sub=None, stereo=None):
    s = ""
    if stereo: s += f'<text x="{x}" y="{y-62}" text-anchor="middle" font-size="15" font-style="italic" fill="#334155">«{stereo}»</text>'
    s += f'<circle cx="{x}" cy="{y-36}" r="15" fill="#fff" stroke="#334155" stroke-width="2.2"/>'
    s += f'<path d="M{x},{y-21} V{y+24} M{x-28},{y-8} H{x+28} M{x},{y+24} L{x-24},{y+58} M{x},{y+24} L{x+24},{y+58}" stroke="#334155" stroke-width="2.2" fill="none"/>'
    s += f'<text x="{x}" y="{y+82}" text-anchor="middle" font-size="19" font-weight="700" fill="#0f172a">{name}</text>'
    for i, t in enumerate(sub or []): s += f'<text x="{x}" y="{y+103+i*17}" text-anchor="middle" font-size="13.5" fill="#475569">{t}</text>'
    a(s)

LE = UX - UCW / 2 + 6
RX, RY = 135, 150; CX, CY = 135, 330
KX, KY = 135, y_sig + 130           # contractor
AX, AY = 135, y_adm + 520            # admin
OX, OY = 1620, y_adm + 380            # OpenAI
# regulator: map only. citizen: all public. contractor: the signed-in band. admin: the signed-in band and all admin functions
line(RX + 30, RY - 5, LE, pos["map"][1])
for k, _ in PUBLIC: line(CX + 30, CY - 5, LE, pos[k][1])
for k, _ in SIGNED: line(KX + 30, KY - 5, LE, pos[k][1])
for k, _ in ADMIN: line(AX + 30, AY - 5, LE, pos[k][1])

# GPT-4o bus
BUSX = 1370; ys = []
for k in GPT:
    x, yy = pos[k]; ys.append(yy)
    a(f'<path d="M{x+UCW/2-4},{yy} H{BUSX}" stroke="#0d9488" stroke-width="1.8" fill="none"/><circle cx="{BUSX}" cy="{yy}" r="4" fill="#0d9488"/>')
a(f'<path d="M{BUSX},{min(ys)} V{max(ys)}" stroke="#0d9488" stroke-width="1.8" fill="none"/><path d="M{BUSX},{OY-5} H{OX-34}" stroke="#0d9488" stroke-width="1.8" fill="none"/>')

for k, l in PUBLIC + SIGNED + ADMIN: uc(pos[k][0], pos[k][1], l)

# Sign in sits between the signed-in band and the admin band so both reach it
SX, SY, SIW, SIH = 1140, y_adm - 10, 210, 150
a(f'<ellipse cx="{SX}" cy="{SY}" rx="{SIW/2}" ry="{SIH/2}" fill="#fff" stroke="#334155" stroke-width="2"/><text x="{SX}" y="{SY+6}" text-anchor="middle" font-size="18" font-weight="700" fill="#0f172a">Sign in</text>')
inc = [k for k, _ in SIGNED] + [k for k, _ in ADMIN if k not in ("note", "tkt", "acc")]   # an extension runs inside its base function, so only the base includes Sign in
for n, k in enumerate(inc):
    x, yy = pos[k]
    above = yy < SY
    y1 = yy + UCH / 2 * math.sin(math.radians(40)) * (-1 if not above else 1) * (1 if above else -1)
    y1 = yy + (UCH / 2 * 0.64) * (1 if above else -1)
    x1 = x + UCW / 2 * math.cos(math.radians(40))
    t = math.radians(-68 + 136 * n / (len(inc) - 1))
    ex = SX - SIW / 2 * math.cos(t); ey = SY + SIH / 2 * math.sin(t)
    line(x1, y1, ex, ey, dash="7 5", mk=True, w=1.5)
    f = 0.30; mx, my = x1 + (ex - x1) * f, y1 + (ey - y1) * f
    a(f'<rect x="{mx-33}" y="{my-9}" width="66" height="17" fill="#fff" opacity="0.9"/><text x="{mx}" y="{my+4}" text-anchor="middle" font-size="12" font-style="italic" fill="#334155">«include»</text>')

# extends: extension -> base, drawn left of the ovals
for ext, base in EXTENDS:
    ex_, ey_ = pos[ext]; bx, by = pos[base]
    xx = UX - 110
    y1, y2 = (ey_ - UCH / 2 + 3, by + UCH / 2 - 3) if ey_ > by else (ey_ + UCH / 2 - 3, by - UCH / 2 + 3)
    line(xx, y1, xx, y2, dash="7 5", mk=True, w=1.6)
    a(f'<rect x="{xx-86}" y="{(y1+y2)/2-9}" width="70" height="17" fill="#fff" opacity="0.85"/><text x="{xx-51}" y="{(y1+y2)/2+4}" text-anchor="middle" font-size="12" font-style="italic" fill="#334155">«extend»</text>')

actor(RX, RY, "Regulator", ["reads the public dashboard"])
actor(CX, CY, "Citizen", ["no account"])
actor(KX, KY, "Contractor", ["sees only its own tickets"])
actor(AX, AY, "Admin", ["national admin, or limited", "to one authority"])
actor(OX, OY, "OpenAI API", ["(GPT-4o)"], stereo="system")

LX, LY = 1420, H - 235
a(f'<rect x="{LX}" y="{LY}" width="320" height="205" rx="10" fill="#fff" stroke="#cbd5e1"/><text x="{LX+15}" y="{LY+24}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">LEGEND</text>')
a(f'<line x1="{LX+17}" y1="{LY+50}" x2="{LX+75}" y2="{LY+50}" stroke="#334155" stroke-width="1.8"/><text x="{LX+87}" y="{LY+55}" font-size="14" fill="#0f172a">actor uses function</text>')
a(f'<line x1="{LX+17}" y1="{LY+78}" x2="{LX+75}" y2="{LY+78}" stroke="#0d9488" stroke-width="1.8"/><text x="{LX+87}" y="{LY+83}" font-size="14" fill="#0f172a">function calls GPT-4o</text>')
a(f'<line x1="{LX+17}" y1="{LY+106}" x2="{LX+75}" y2="{LY+106}" stroke="#334155" stroke-width="1.6" stroke-dasharray="7 5" marker-end="url(#op)"/><text x="{LX+87}" y="{LY+111}" font-size="14" fill="#0f172a">include / extend</text>')
for i, t in enumerate(["Include: the function needs Sign in first.", "Extend: optional step added to a function.", "Risk scoring runs the XGBoost model on this", "server; it also runs on a schedule."]):
    a(f'<text x="{LX+15}" y="{LY+138+i*18}" font-size="12.5" fill="#475569">{t}</text>')
a("</svg>")
open(os.path.join(HERE, "ISJ107V_A5_Q3.1_UseCase.svg"), "w").write("\n".join(o))
print("use-case svg written", W, H)
