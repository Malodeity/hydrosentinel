import math
out=[]; BOX={}
HDR,ROW=36,19
def esc(s): return s.replace("<","&lt;").replace(">","&gt;")
def cls(key,name,attrs,ops,x,y,w,stereo=None,fill="#f6f6f6"):
    h=HDR+(14 if stereo else 0)+len(attrs)*ROW+8+max(len(ops),0)*ROW+8
    if not ops: h=HDR+(14 if stereo else 0)+len(attrs)*ROW+10
    BOX[key]=(x,y,w,h)
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#222" stroke-width="1.5"/>')
    ty=y+22
    if stereo:
        out.append(f'<text x="{x+w/2}" y="{y+16}" text-anchor="middle" font-size="12" font-style="italic">«{stereo}»</text>'); ty+=14
    out.append(f'<text x="{x+w/2}" y="{ty}" text-anchor="middle" font-size="15" font-weight="bold">{name}</text>')
    ay=y+HDR+(14 if stereo else 0)
    out.append(f'<line x1="{x}" y1="{ay}" x2="{x+w}" y2="{ay}" stroke="#222" stroke-width="1.2"/>')
    for i,a in enumerate(attrs):
        out.append(f'<text x="{x+10}" y="{ay+15+i*ROW}" font-size="12.5" font-family="Menlo, Consolas, monospace">{esc(a)}</text>')
    oy=ay+len(attrs)*ROW+8 if attrs else ay+8
    if ops:
        out.append(f'<line x1="{x}" y1="{oy}" x2="{x+w}" y2="{oy}" stroke="#222" stroke-width="1.2"/>')
        for i,o in enumerate(ops):
            out.append(f'<text x="{x+10}" y="{oy+15+i*ROW}" font-size="12.5" font-family="Menlo, Consolas, monospace">{esc(o)}</text>')
def line(pts,dash=False):
    d=" ".join(f"{x:.0f},{y:.0f}" for x,y in pts)
    out.append(f'<polyline points="{d}" fill="none" stroke="#222" stroke-width="1.4"{" stroke-dasharray=\"6 4\"" if dash else ""}/>')
def diamond(p,q):
    dx,dy=q[0]-p[0],q[1]-p[1]; L=math.hypot(dx,dy); ux,uy=dx/L,dy/L
    px,py=-uy,ux; a,b=9,16
    pts=[p,(p[0]+ux*b/2+px*a/2*0.9,p[1]+uy*b/2+py*a/2*0.9),(p[0]+ux*b,p[1]+uy*b),(p[0]+ux*b/2-px*a/2*0.9,p[1]+uy*b/2-py*a/2*0.9)]
    out.append('<polygon points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)+'" fill="#222" stroke="#222"/>')
def txt(x,y,s,anchor="middle",size=13,bold=False,italic=False):
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}"{" font-weight=\"bold\"" if bold else ""}{" font-style=\"italic\"" if italic else ""}>{esc(s)}</text>')
def label(x,y,s,anchor="middle"):
    w=len(s)*7.2+6
    ax=x-w/2 if anchor=="middle" else (x-3 if anchor=="start" else x-w+3)
    out.append(f'<rect x="{ax:.0f}" y="{y-12}" width="{w:.0f}" height="17" fill="#fff"/>')
    txt(x,y,s,anchor)

W,H=1440,1340
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
txt(W/2,32,"HydroSentinel: Class Diagram",size=19,bold=True)

cls('user','User',["+ id : UUID","+ email : String","+ hashed_password : String","+ role : UserRole","+ is_active : Boolean","+ last_login_at : DateTime","+ created_at : DateTime"],
    ["+ verifyPassword(plain) : Boolean"],40,70,320)
cls('audit','AuditLog',["+ id : UUID","+ user_id : UUID","+ action : AuditAction","+ table_name : String","+ record_id : UUID","+ old_value : JSON","+ new_value : JSON","+ ip_address : String","+ created_at : DateTime"],
    [],450,70,320)
cls('wsa','WSA',["+ id : UUID","+ name : String","+ province : String","+ blue_drop_score : Float","+ green_drop_score : Float","+ nrw_percent : Float","+ maint_pct : Float","+ risk_level : RiskLevel","+ cap_status : CAPStatus","+ cap_due_date : Date","+ lat, lng : Float"],
    ["+ updateCapStatus(status, dueDate)"],920,70,420)
cls('tok','RefreshToken',["+ id : UUID","+ user_id : UUID","+ token_hash : String","+ expires_at : DateTime","+ revoked_at : DateTime","+ created_at : DateTime"],
    ["+ rotate() : RefreshToken"],40,500,320)
cls('rep','CitizenReport',["+ id : UUID","+ wsa_id : UUID","+ issue_type : IssueType","+ reference_code : String","+ description : String","+ case_status : String","+ admin_comment : String","+ reviewed_by : UUID","+ resolved_by : UUID","+ reviewed_at : DateTime","+ resolved_at : DateTime","+ lat, lng : Float","+ created_at : DateTime"],
    ["+ updateCaseStatus(status, comment)"],450,500,320)
cls('hist','RiskScoreHistory',["+ id : UUID","+ wsa_id : UUID","+ risk_level : RiskLevel","+ probability : Float","+ model_source : ModelSource","+ model_version : String","+ scored_by : UUID","+ scored_at : DateTime"],
    [],920,500,420)
cls('alert','Alert',["+ id : UUID","+ wsa_id : UUID","+ alert_type : AlertType","+ message : String","+ acknowledged_by : UUID","+ acknowledged_at : DateTime","+ created_at : DateTime"],
    ["+ acknowledge(user)"],920,790,420)
cls('sum','Summary',["+ id : UUID","+ content : String","+ generated_by : UUID","+ generated_at : DateTime"],
    ["+ isFresh(hours) : Boolean"],40,800,320)

def B(k): return BOX[k]
u,a,w,t,r,h,al=[B(k) for k in ('user','audit','wsa','tok','rep','hist','alert')]
# 1 User composes RefreshToken
line([(200,u[1]+u[3]),(200,t[1])]); diamond((200,u[1]+u[3]),(200,t[1]))
label(228,u[1]+u[3]+30,"1","start"); label(228,t[1]-10,"0..*","start"); label(232,(u[1]+u[3]+t[1])/2+4,"owns","start")
# 2 User -> AuditLog
line([(u[0]+u[2],150),(a[0],150)])
label(u[0]+u[2]+16,142,"1"); label(a[0]-22,142,"0..*"); label((u[0]+u[2]+a[0])/2,178,"performs")
# 3 User -> CitizenReport (reviews/resolves)
line([(u[0]+u[2],u[1]+u[3]-22),(405,u[1]+u[3]-22),(405,r[1]+70),(r[0],r[1]+70)])
label(u[0]+u[2]+22,u[1]+u[3]-30,"0..1"); label(r[0]-24,r[1]+62,"0..*")
label(418,r[1]-104,"reviews / resolves","start")
# 4 WSA composes CitizenReport
line([(w[0],170),(845,170),(845,r[1]+120),(r[0]+r[2],r[1]+120)]); diamond((w[0],170),(845,170))
label(w[0]-22,162,"1"); label(r[0]+r[2]+26,r[1]+112,"0..*"); txt(845,r[1]-40,"receives",size=13)
# 5 WSA composes RiskScoreHistory
cx=1130
line([(cx,w[1]+w[3]),(cx,h[1])]); diamond((cx,w[1]+w[3]),(cx,h[1]))
label(cx+18,w[1]+w[3]+30,"1","start"); label(cx+18,h[1]-10,"0..*","start"); label(cx+24,(w[1]+w[3]+h[1])/2+4,"has history","start")
# 6 WSA composes Alert
line([(w[0]+w[2],w[1]+120),(1405,w[1]+120),(1405,al[1]+60),(al[0]+al[2],al[1]+60)]); diamond((w[0]+w[2],w[1]+120),(1405,w[1]+120))
label(w[0]+w[2]+22,w[1]+112,"1"); label(al[0]+al[2]+30,al[1]+50,"0..*")
label(1405,al[1]-30,"triggers")

# notes
def note(x,y,w_,lines):
    hh=14+len(lines)*17
    out.append(f'<path d="M{x} {y}H{x+w_-14}L{x+w_} {y+14}V{y+hh}H{x}Z" fill="#fffbe6" stroke="#222" stroke-width="1.2"/><path d="M{x+w_-14} {y}V{y+14}H{x+w_}" fill="none" stroke="#222" stroke-width="1.2"/>')
    for i,l in enumerate(lines): txt(x+10,y+22+i*17,l,anchor="start",size=12)
    return hh
note(450,880,400,["Other associations to User (each 0..1, ON DELETE SET NULL):","RiskScoreHistory.scored_by, Alert.acknowledged_by,","Summary.generated_by. Not drawn, to keep lines readable."])
note(450,975,400,["Photos are stored on disk (/uploads/{report_id}/),","not as a CitizenReport column.","No inheritance: no domain class specialises another."])

# enumerations
txt(40,1085,"Enumerations used as attribute types",anchor="start",size=15,bold=True)
def enum(x,y,name,vals,w_=190):
    hh=36+14+len(vals)*ROW+6
    out.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{hh}" fill="#eef3fb" stroke="#222" stroke-width="1.3"/>')
    txt(x+w_/2,y+15,"«enumeration»",size=11,italic=True); txt(x+w_/2,y+32,name,size=14,bold=True)
    out.append(f'<line x1="{x}" y1="{y+40}" x2="{x+w_}" y2="{y+40}" stroke="#222"/>')
    for i,v in enumerate(vals): out.append(f'<text x="{x+10}" y="{y+56+i*ROW}" font-size="12.5" font-family="Menlo, Consolas, monospace">{v}</text>')
Y=1105
enum(40,Y,"RiskLevel",["low","medium","high"],w_=170)
enum(220,Y,"CAPStatus",["none","submitted","in_progress","completed"],w_=170)
enum(400,Y,"IssueType",["leak","outage","quality","billing"],w_=170)
enum(580,Y,"ModelSource",["xgboost","heuristic"],w_=170)
enum(760,Y,"UserRole",["admin","viewer"],w_=170)
enum(950,Y,"AlertType",["risk_level_high","risk_level_increased","report_volume_spike","cap_overdue","geo_cluster_incident"],w_=210)
enum(1180,Y,"AuditAction",["cap_status_updated","report_status_updated","report_comment_updated","risk_score_run","wsa_updated","user_created","summary_generated"],w_=240)
out.append('</svg>')
open('4.3-class.svg','w').write("\n".join(out))
