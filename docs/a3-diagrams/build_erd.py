out=[]; BOX={}
ROW=19; HDR=34
def esc(s): return s.replace("<","&lt;").replace(">","&gt;")
def table(key,name,cols,x,y,w):
    h=HDR+len(cols)*ROW+10
    BOX[key]=(x,y,w,h)
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f6f6f6" stroke="#222" stroke-width="1.5"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HDR-4}" fill="#dfe8f5" stroke="#222" stroke-width="1.5"/>')
    out.append(f'<text x="{x+w/2}" y="{y+21}" text-anchor="middle" font-size="15" font-weight="bold">{name}</text>')
    for i,(n,t,k) in enumerate(cols):
        yy=y+HDR+15+i*ROW
        out.append(f'<text x="{x+10}" y="{yy}" font-size="12.5" font-family="Menlo, Consolas, monospace">{esc(n)} : {esc(t)}</text>')
        if k: out.append(f'<text x="{x+w-10}" y="{yy}" text-anchor="end" font-size="12" font-weight="bold" fill="#8a1c1c">{esc(k)}</text>')
def line(pts):
    d=" ".join(f"{x:.0f},{y:.0f}" for x,y in pts)
    out.append(f'<polyline points="{d}" fill="none" stroke="#222" stroke-width="1.4"/>')
def txt(x,y,s,anchor="middle",size=13,bold=False):
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}"{" font-weight=\"bold\"" if bold else ""}>{esc(s)}</text>')
def label(x,y,s,anchor="middle"):
    w=len(s)*7+6; ax=x-w/2 if anchor=="middle" else (x-3 if anchor=="start" else x-w+3)
    out.append(f'<rect x="{ax:.0f}" y="{y-12}" width="{w:.0f}" height="17" fill="#fff"/>'); txt(x,y,s,anchor)
def crow(x,y,dx,dy):
    # crow's foot pointing at (x,y) coming from direction (dx,dy) unit
    px,py=-dy,dx
    bx,by=x-dx*14,y-dy*14
    for s in (-8,0,8):
        out.append(f'<line x1="{bx+px*s:.1f}" y1="{by+py*s:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="#222" stroke-width="1.4"/>')
    out.append(f'<line x1="{x-dx*20+px*8:.1f}" y1="{y-dy*20+py*8:.1f}" x2="{x-dx*20-px*8:.1f}" y2="{y-dy*20-py*8:.1f}" stroke="#222" stroke-width="1.4"/>')
def one(x,y,dx,dy):
    px,py=-dy,dx
    for off in (10,15):
        out.append(f'<line x1="{x-dx*off+px*8:.1f}" y1="{y-dy*off+py*8:.1f}" x2="{x-dx*off-px*8:.1f}" y2="{y-dy*off-py*8:.1f}" stroke="#222" stroke-width="1.4"/>')

W,H=1650,1080
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
txt(W/2,32,"HydroSentinel: Entity-Relationship Diagram (PostgreSQL schema)",size=19,bold=True)

table('users','users',[("id","uuid","PK"),("email","varchar(255)","UNIQUE"),("hashed_password","varchar(255)",""),("role","user_role_enum",""),("is_active","boolean",""),("last_login_at","timestamptz","null"),("created_at","timestamptz","")],40,70,360)
table('tok','refresh_tokens',[("id","uuid","PK"),("user_id","uuid","FK users"),("token_hash","varchar(255)","UNIQUE"),("expires_at","timestamptz",""),("revoked_at","timestamptz","null"),("created_at","timestamptz","")],40,480,360)
table('audit','audit_log',[("id","uuid","PK"),("user_id","uuid","FK users"),("action","audit_action_enum",""),("table_name","varchar(100)",""),("record_id","uuid",""),("old_value","jsonb","null"),("new_value","jsonb","null"),("ip_address","varchar(45)","null"),("created_at","timestamptz","")],440,480,360)
table('sum','summaries',[("id","uuid","PK"),("content","text",""),("generated_by","uuid","FK users, null"),("generated_at","timestamptz","")],40,850,360)
table('wsa','wsa',[("id","uuid","PK"),("name","varchar(255)","UNIQUE"),("province","varchar(100)",""),("blue_drop_score","numeric(5,2)","null"),("green_drop_score","numeric(5,2)","null"),("nrw_percent","numeric(5,2)","null"),("maint_pct","numeric(5,2)","null"),("cap_status","cap_status_enum",""),("cap_due_date","date","null"),("risk_level","risk_level_enum",""),("bdrr_risk_level","risk_level_enum","null"),("lat, lng","numeric(9,6)","")],1000,70,420)
table('rep','citizen_reports',[("id","uuid","PK"),("wsa_id","uuid","FK wsa"),("issue_type","issue_type_enum",""),("reference_code","varchar(12)","UNIQUE"),("case_status","varchar(50)",""),("description","text","null"),("admin_comment","text","null"),("reviewed_by","uuid","FK users, null"),("resolved_by","uuid","FK users, null"),("reviewed_at","timestamptz","null"),("resolved_at","timestamptz","null"),("lat, lng","numeric(9,6)",""),("created_at","timestamptz","")],820,480,360)
table('hist','risk_score_history',[("id","uuid","PK"),("wsa_id","uuid","FK wsa"),("risk_level","risk_level_enum",""),("probability","numeric(6,4)",""),("model_source","model_source_enum",""),("model_version","varchar(50)","null"),("scored_by","uuid","FK users, null"),("scored_at","timestamptz","")],1200,480,360)
table('alert','alerts',[("id","uuid","PK"),("wsa_id","uuid","FK wsa"),("alert_type","alert_type_enum",""),("message","text",""),("acknowledged_by","uuid","FK users, null"),("acknowledged_at","timestamptz","null"),("created_at","timestamptz","")],1200,780,360)

B=BOX
u,t,a,w,r,h,al=[B[k] for k in ('users','tok','audit','wsa','rep','hist','alert')]
# users -> refresh_tokens
x=220; line([(x,u[1]+u[3]),(x,t[1])]); one(x,u[1]+u[3],0,-1); crow(x,t[1],0,1)
label(x+70,(u[1]+u[3]+t[1])/2+4,"owns (CASCADE)","start")
# users -> audit_log
line([(u[0]+u[2],210),(620,210),(620,a[1])]); one(u[0]+u[2],210,-1,0); crow(620,a[1],0,1)
label(640,300,"performs (RESTRICT)","start")
# wsa -> citizen_reports
x=1050; line([(x,w[1]+w[3]),(x,r[1]+0)]) if False else None
line([(1060,w[1]+w[3]),(1060,r[1])]); one(1060,w[1]+w[3],0,-1); crow(1060,r[1],0,1)
label(1075,(w[1]+w[3]+r[1])/2+4,"receives (CASCADE)","start")
# wsa -> risk_score_history
line([(1330,w[1]+w[3]),(1330,h[1])]); one(1330,w[1]+w[3],0,-1); crow(1330,h[1],0,1)
label(1345,(w[1]+w[3]+h[1])/2+4,"has (CASCADE)","start")
# wsa -> alerts
line([(w[0]+w[2],150),(1610,150),(1610,al[1]+60),(al[0]+al[2],al[1]+60)]); one(w[0]+w[2],150,-1,0); crow(al[0]+al[2],al[1]+60,-1,0)
label(1500,140,"raises (CASCADE)")

def note(x,y,w_,lines):
    hh=14+len(lines)*17
    out.append(f'<path d="M{x} {y}H{x+w_-14}L{x+w_} {y+14}V{y+hh}H{x}Z" fill="#fffbe6" stroke="#222" stroke-width="1.2"/><path d="M{x+w_-14} {y}V{y+14}H{x+w_}" fill="none" stroke="#222" stroke-width="1.2"/>')
    for i,l in enumerate(lines): txt(x+10,y+22+i*17,l,anchor="start",size=12)
note(440,850,340,["Every FK to users (reviewed_by, resolved_by,","scored_by, acknowledged_by, generated_by) is","nullable and uses ON DELETE SET NULL, so","deleting a user never deletes records."])
note(440,960,340,["Notation: one bar = exactly one, crow's foot =","zero or more. 'null' marks a nullable column."])
note(820,850,340,["Photos are files on disk under","uploads/{report_id}/, not a column.","enum types (cap_status_enum etc.) are","PostgreSQL enumerated types."])
out.append('</svg>')
open('A3-4.2-erd.svg','w').write("\n".join(out))
