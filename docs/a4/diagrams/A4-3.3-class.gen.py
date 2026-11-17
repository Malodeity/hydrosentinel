import html
W,H=2000,1580
o=[];a=o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
a('<defs><marker id="op" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto"><path d="M1,1 L11,6 L1,11" fill="none" stroke="#334155" stroke-width="1.6"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="28" font-weight="700" fill="#0f172a">HydroSentinel prototype: Class Diagram</text>')
LH=22
B={}
def box(key,x,y,w,title,attrs=(),ops=(),stereo=None,fill='#ffffff',head='#e0f2fe',cols=1):
    hh=(52 if stereo else 36)
    rows=(len(attrs)+cols-1)//cols
    ah=max(rows,0)*LH+14 if attrs else 8
    oh=len(ops)*LH+14 if ops else 0
    h=hh+ah+oh
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#334155" stroke-width="2"/>')
    a(f'<path d="M{x},{y+hh} V{y+6} Q{x},{y} {x+6},{y} H{x+w-6} Q{x+w},{y} {x+w},{y+6} V{y+hh} Z" fill="{head}" stroke="#334155" stroke-width="2"/>')
    if stereo: a(f'<text x="{x+w/2}" y="{y+19}" text-anchor="middle" font-size="14" font-style="italic" fill="#334155">«{stereo}»</text>')
    a(f'<text x="{x+w/2}" y="{y+hh-11}" text-anchor="middle" font-size="19" font-weight="700" fill="#0f172a">{title}</text>')
    cw=w/cols
    for i,t in enumerate(attrs):
        c,r=i//rows,i%rows
        a(f'<text x="{x+12+c*cw}" y="{y+hh+20+r*LH}" font-size="14.5" fill="#0f172a">{html.escape(t)}</text>')
    if ops:
        yy=y+hh+ah
        a(f'<line x1="{x}" y1="{yy}" x2="{x+w}" y2="{yy}" stroke="#334155" stroke-width="1.5"/>')
        for i,t in enumerate(ops): a(f'<text x="{x+12}" y="{yy+20+i*LH}" font-size="14.5" fill="#0f172a">{html.escape(t)}</text>')
    B[key]=(x,y,w,h)
def ln(x1,y1,x2,y2,dash=None,mk=False,col='#334155',w=1.9):
    d=f' stroke-dasharray="7 5"' if dash else ''
    m=' marker-end="url(#op)"' if mk else ''
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d}{m}/>')
def poly(pts,dash=None,mk=False,col='#334155',w=1.9):
    d=f' stroke-dasharray="7 5"' if dash else ''
    m=' marker-end="url(#op)"' if mk else ''
    a(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{col}" stroke-width="{w}"{d}{m}/>')
def t(x,y,s,anchor='middle',size=13.5,it=False,bg=True):
    if bg: a(f'<rect x="{x-len(s)*3.6-3 if anchor=="middle" else x-3}" y="{y-12}" width="{len(s)*7.2+6}" height="17" fill="#fff"/>')
    a(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" {"font-style=\"italic\"" if it else ""} fill="#334155">{html.escape(s)}</text>')
def mult(x,y,s,anchor='start'): a(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="14" font-weight="700" fill="#0f172a">{s}</text>')

# ---- layout
DX0,DX1=370,1470          # data block x range
# User (top)
box('user',DX0,80,DX1-DX0,'User',['id : UUID','email : String','hashed_password : String','role : UserRole','is_active : Boolean','last_login_at : DateTime','created_at : DateTime'],cols=2,head='#dbeafe')
# middle row
my=420
box('hist',DX0,my,320,'RiskScoreHistory',['id : UUID','risk_level : RiskLevel','probability : Float','model_source : ModelSource','model_version : String','scored_at : DateTime'])
box('rep',DX0+360,my,390,'CitizenReport',['id : UUID','issue_type : IssueType','description : String','reference_code : String','case_status : String','admin_comment : String','lat : Float','lng : Float','photo_analysis : JSON','reviewed_at : DateTime','resolved_at : DateTime','created_at : DateTime'])
box('alert',DX0+790,my,DX1-DX0-790,'Alert',['id : UUID','alert_type : AlertType','message : String','acknowledged_at : DateTime','created_at : DateTime'])
# WSA (bottom)
box('wsa',DX0,860,DX1-DX0,'WSA',['id : UUID','name : String','province : String','blue_drop_score : Float','nrw_percent : Float','maint_pct : Float','cap_status : CAPStatus','cap_due_date : Date','risk_level : RiskLevel','lat : Float','lng : Float','updated_at : DateTime'],cols=2,head='#dbeafe')
# right column
RX=1650;RW=330
box('rt',RX,80,RW,'RefreshToken',['token_hash : String','expires_at : DateTime','revoked_at : DateTime'])
box('sum',RX,250,RW,'Summary',['id : UUID','content : String','generated_at : DateTime'])
box('aud',RX,420,RW,'AuditLog',['id : UUID','action : AuditAction','table_name : String','record_id : UUID','old_value : JSON','new_value : JSON','ip_address : String','created_at : DateTime'])
# services
S='#fef3c7'
box('auds',RX,720,RW,'AuditService',[],['write_audit(db, user, action,','    table, record, old, new)'],stereo='service',head=S)
box('alrs',RX,860,RW,'AlertService',[],['raise_high_risk_alert(wsa, db)','raise_risk_increased_alert(...)','raise_report_volume_spike_alert(..)','raise_geo_cluster_alert(...)','raise_cap_overdue_alerts(db)','resolve_stale_alerts(db)'],stereo='service',head=S)
box('rm',30,420,250,'RiskModel',[],['predict_wsa_risk(wsa)',': RiskResult'],stereo='service',head=S)
box('ai',30,980,250,'AiService',[],['call_openai(system, user)','get_cap_draft(wsa_id)','analyze_report_photo(id)','run_query_agent(question)'],stereo='service',head=S)

def X(k): x,y,w,h=B[k];return x,y,w,h
# ---- associations User -> middle row (vertical) and middle row -> WSA (vertical)
ux,uy,uw,uh=X('user');ub=uy+uh
for k,cx,nm,m1,m2 in (('hist',None,'scores','0..1','0..*'),('rep',None,'reviews / resolves','0..1','0..*'),('alert',None,'acknowledges','0..1','0..*')):
    x,y,w,h=X(k);cx=x+w/2
    ln(cx,ub,cx,y)
    mult(cx+8,ub+18,m1);mult(cx+8,y-8,m2)
    t(cx,(ub+y)/2+5,nm)
wx,wy,ww,wh=X('wsa')
for k,nm in (('hist','scored over time'),('rep','receives'),('alert','raises')):
    x,y,w,h=X(k);cx=x+w/2
    ln(cx,y+h,cx,wy)
    mult(cx+8,y+h+18,'0..*');mult(cx+8,wy-8,'1')
    t(cx,(y+h+wy)/2+5,nm)
# ---- User -> right column: three separate exits
ys=[B['rt'][1]+28,B['sum'][1]+28,B['aud'][1]+28]
e1,e2,e3=uy+30,uy+80,uy+130
ln(DX1,ys[0],RX,ys[0])
mult(DX1+8,ys[0]-6,'1');mult(RX-8,ys[0]-6,'0..*','end');t((DX1+RX)/2,ys[0]-6,'holds')
poly([(DX1,e2),(1600,e2),(1600,ys[1]),(RX,ys[1])])
mult(DX1+8,e2-6,'0..1');mult(RX-8,ys[1]-6,'0..*','end');t(1592,(e2+ys[1])/2+4,'generates','end')
poly([(DX1,e3),(1550,e3),(1550,ys[2]),(RX,ys[2])])
mult(DX1+8,e3-6,'1');mult(RX-8,ys[2]-6,'0..*','end');t(1542,(e3+ys[2])/2+4,'performs','end')
# ---- dependencies (service -> class)
hx,hy,hw,hh=X('hist');rx_,ry_,rw_,rh_=X('rm')
ln(rx_+rw_,hy+hh/2,hx,hy+hh/2,dash=True,mk=True);t((rx_+rw_+hx)/2,hy+hh/2-8,'saves')
# RiskModel -> WSA (reads): down the left edge
poly([(rx_+rw_/2,rh_+hy),(rx_+rw_/2,wy+60),(wx,wy+60)],dash=True,mk=True);t(rx_+rw_/2+50,wy+52,'reads',bg=True)
ax,ay,aw,ah=X('ai')
poly([(ax+aw,ay+30),(wx-0,ay+30)],dash=True,mk=True) if False else None
ln(ax+aw,ay+40,wx,ay+40,dash=True,mk=True);t((ax+aw+wx)/2,ay+32,'reads')
ln(DX1,ay+40,DX1,ay+40)
# AlertService -> Alert (creates): elbow
alx,aly,alw,alh=X('alrs');alx_,aly_,alw_,alh_=X('alert')
poly([(alx,aly+30),(DX1+40,aly+30),(DX1+40,aly_+alh_/2),(DX1,aly_+alh_/2)],dash=True,mk=True);t(DX1+110,aly+22,'creates')
# AuditService -> AuditLog (writes): vertical
asx,asy,asw,ash=X('auds');lx,ly,lw,lh=X('aud')
ln(asx+asw/2,asy,asx+asw/2,ly+lh,dash=True,mk=True);t(asx+asw/2+42,(asy+ly+lh)/2+4,'writes')
# ---- enumerations strip
ey=1290
a(f'<text x="30" y="{ey-14}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">ENUMERATIONS USED BY THE ATTRIBUTES ABOVE</text>')
E='#ede9fe'
enums=[('CAPStatus',['none','submitted','in_progress','completed']),('RiskLevel',['low','medium','high']),('IssueType',['leak','outage','quality','billing']),('ModelSource',['xgboost','heuristic']),('AlertType',['risk_level_high','risk_level_increased','report_volume_spike','cap_overdue','geo_cluster_incident']),('AuditAction',['cap_status_updated','report_status_updated','report_comment_updated','risk_score_run','wsa_updated','user_created','summary_generated']),('UserRole',['admin','viewer'])]
x=30
for nm,vals in enums:
    w=max(170,max(len(v) for v in vals)*8.4+28)
    box('e_'+nm,x,ey,w,nm,vals,stereo='enumeration',head=E)
    x+=w+16
a('</svg>')
open('A4-3.3-class.svg','w').write('\n'.join(o))
