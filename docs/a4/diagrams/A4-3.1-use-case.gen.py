import html,math
W,H=1700,1580
o=[];a=o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
a('<defs><marker id="op" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto"><path d="M1,1 L11,6 L1,11" fill="none" stroke="#334155" stroke-width="1.6"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="28" font-weight="700" fill="#0f172a">HydroSentinel prototype: Use-Case Diagram (demonstrated functions)</text>')
BX,BY,BW,BH=340,80,1040,1450
a(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="14" fill="#f8fafc" stroke="#475569" stroke-width="2.2"/>')
a(f'<text x="{BX+BW/2}" y="{BY+34}" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">HydroSentinel prototype</text>')
def band(y,h,label,col):
    a(f'<rect x="{BX+14}" y="{y}" width="{BW-28}" height="{h}" rx="10" fill="{col}" opacity="0.55"/>')
    a(f'<text x="{BX+30}" y="{y+24}" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">{label}</text>')
band(120,330,'PUBLIC FUNCTIONS (NO SIGN-IN)','#e0f2fe')
band(470,1040,'ADMIN FUNCTIONS (SIGN-IN REQUIRED)','#fef3c7')
UCW,UCH=390,54
UX=610
def uc(cx,cy,lines):
    a(f'<ellipse cx="{cx}" cy="{cy}" rx="{UCW/2}" ry="{UCH/2}" fill="#fff" stroke="#334155" stroke-width="2"/>')
    n=len(lines)
    for i,l in enumerate(lines):
        a(f'<text x="{cx}" y="{cy+5+(i-(n-1)/2)*19}" text-anchor="middle" font-size="16.5" fill="#0f172a">{html.escape(l)}</text>')
pub=[('map',['View risk map and','AI summaries'],210),('sub',['Submit report','with photos'],300),('trk',['Track report by','reference code'],390)]
adm=[('tri',['Triage report']),('note',['Draft AI case note']),('pho',['Check photo with AI']),('scr',['Score WSA risk (XGBoost)']),('cap',['Update CAP status and deadline']),('dft',['Draft CAP with AI']),('acc',['Accept CAP item']),('ask',['Ask AI about data or regulations']),('brf',['Get AI briefing and recommendations']),('alr',['Review and acknowledge alerts']),('aud',['View audit log']),('usr',['Manage admin users']),('exp',['Export data and management report'])]
pos={k:(UX,y) for k,_,y in pub}
y=545
for k,_ in adm: pos[k]=(UX,y);y+=70
SX,SY=1140,790;SIW,SIH=210,150
def actor(x,y,name,sub=None,stereo=None):
    s=''
    if stereo: s+=f'<text x="{x}" y="{y-62}" text-anchor="middle" font-size="15" font-style="italic" fill="#334155">«{stereo}»</text>'
    s+=f'<circle cx="{x}" cy="{y-36}" r="15" fill="#fff" stroke="#334155" stroke-width="2.2"/>'
    s+=f'<path d="M{x},{y-21} V{y+24} M{x-28},{y-8} H{x+28} M{x},{y+24} L{x-24},{y+58} M{x},{y+24} L{x+24},{y+58}" stroke="#334155" stroke-width="2.2" fill="none"/>'
    s+=f'<text x="{x}" y="{y+82}" text-anchor="middle" font-size="19" font-weight="700" fill="#0f172a">{name}</text>'
    for i,t in enumerate(sub or []): s+=f'<text x="{x}" y="{y+103+i*17}" text-anchor="middle" font-size="13.5" fill="#475569">{t}</text>'
    a(s)
CX,CY=135,330;RX,RY=135,150;AX,AY=135,1000;OX,OY=1560,700
def line(x1,y1,x2,y2,col='#334155',dash=None,mk=False,w=1.8):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    m=' marker-end="url(#op)"' if mk else ''
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d}{m}/>')
LE=UX-UCW/2+6
# Regulator: only the map. Citizen: all three public functions.
line(RX+30,RY-5,LE,pos['map'][1])
for k in ('map','sub','trk'): 
    if k!='map' or True: line(CX+30,CY-5,LE,pos[k][1])
for k,_ in adm: line(AX+30,AY-5,LE,pos[k][1])
# AI bus
BUSX=1330;ys=[]
for k in ('map','sub','note','pho','dft','ask','brf'):
    x,yy=pos[k];ys.append(yy)
    a(f'<path d="M{x+UCW/2-4},{yy} H{BUSX}" stroke="#0d9488" stroke-width="1.8" fill="none"/><circle cx="{BUSX}" cy="{yy}" r="4" fill="#0d9488"/>')
a(f'<path d="M{BUSX},{min(ys)} V{max(ys)}" stroke="#0d9488" stroke-width="1.8" fill="none"/><path d="M{BUSX},{OY-5} H{OX-34}" stroke="#0d9488" stroke-width="1.8" fill="none"/>')
for k,l,y in pub: uc(UX,y,l)
for k,l in adm: uc(pos[k][0],pos[k][1],l)
a(f'<ellipse cx="{SX}" cy="{SY}" rx="{SIW/2}" ry="{SIH/2}" fill="#fff" stroke="#334155" stroke-width="2"/><text x="{SX}" y="{SY+6}" text-anchor="middle" font-size="18" font-weight="700" fill="#0f172a">Sign in</text>')
# include arrows: start low/high on the oval (not on the centre line used by the GPT-4o link), end spread around the left of Sign in
inc=['tri','pho','scr','cap','dft','ask','brf','alr','aud','usr','exp']
for n,k in enumerate(inc):
    x,yy=pos[k]
    below = (n/(len(inc)-1))<0.5
    ang=math.radians(40 if below else -40)
    x1=x+UCW/2*math.cos(ang); y1=yy+UCH/2*math.sin(ang)*(1 if below else -1)*(1 if below else -1)
    y1=yy+UCH/2*math.sin(math.radians(40))*(1 if below else -1)
    t=math.radians(-68+136*n/(len(inc)-1))
    ex=SX-SIW/2*math.cos(t); ey=SY+SIH/2*math.sin(t)
    line(x1,y1,ex,ey,dash='7 5',mk=True,w=1.6)
    f=0.30;mx,my=x1+(ex-x1)*f,y1+(ey-y1)*f
    a(f'<rect x="{mx-33}" y="{my-9}" width="66" height="17" fill="#fef3c7"/><text x="{mx}" y="{my+4}" text-anchor="middle" font-size="12" font-style="italic" fill="#334155">«include»</text>')
# extends: ext -> base (arrow ends at base)
for ext,base in (('note','tri'),('acc','dft')):
    ex_,ey_=pos[ext];bx,by=pos[base]
    xx=UX-110
    if ey_>by: y1,y2=ey_-UCH/2+3,by+UCH/2-3
    else: y1,y2=ey_+UCH/2-3,by-UCH/2+3
    line(xx,y1,xx,y2,dash='7 5',mk=True,w=1.6)
    a(f'<rect x="{xx-86}" y="{(y1+y2)/2-9}" width="70" height="17" fill="#fef3c7"/><text x="{xx-51}" y="{(y1+y2)/2+4}" text-anchor="middle" font-size="12" font-style="italic" fill="#334155">«extend»</text>')
actor(RX,RY,'Regulator',['reads the public dashboard'])
actor(CX,CY,'Citizen',['no account'])
actor(AX,AY,'Admin',['staff with the admin role'])
actor(OX,OY,'OpenAI API',['(GPT-4o)'],stereo='system')
a('<rect x="1395" y="1330" width="285" height="180" rx="10" fill="#fff" stroke="#cbd5e1"/><text x="1410" y="1354" font-size="14" font-weight="700" letter-spacing="1.5" fill="#475569">LEGEND</text>')
a('<line x1="1412" y1="1380" x2="1470" y2="1380" stroke="#334155" stroke-width="1.8"/><text x="1482" y="1385" font-size="14" fill="#0f172a">actor uses function</text>')
a('<line x1="1412" y1="1408" x2="1470" y2="1408" stroke="#0d9488" stroke-width="1.8"/><text x="1482" y="1413" font-size="14" fill="#0f172a">function calls GPT-4o</text>')
a('<line x1="1412" y1="1436" x2="1470" y2="1436" stroke="#334155" stroke-width="1.6" stroke-dasharray="7 5" marker-end="url(#op)"/><text x="1482" y="1441" font-size="14" fill="#0f172a">include / extend</text>')
a('<text x="1410" y="1466" font-size="12.5" fill="#475569">Include: the function needs Sign in first.</text><text x="1410" y="1484" font-size="12.5" fill="#475569">Extend: optional step added to a function.</text>')
a('</svg>')
open('A4-3.1-use-case.svg','w').write('\n'.join(o))
