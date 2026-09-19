import math
W,H=1420,1140
RX,RY=100,31
out=[]
def ell(c,label):
    x,y=c
    out.append(f'<ellipse cx="{x}" cy="{y}" rx="{RX}" ry="{RY}" fill="#f6f6f6" stroke="#222" stroke-width="1.4"/>')
    lines=label.split("\n")
    tag=lines[-1] if lines[-1].startswith("(") else None
    body=lines[:-1] if tag else lines
    off=-7*(len(body)-1)+(0 if tag else 5)-(5 if tag else 0)
    for i,l in enumerate(body):
        out.append(f'<text x="{x}" y="{y+off+i*15}" text-anchor="middle" font-size="13">{l}</text>')
    if tag:
        out.append(f'<text x="{x}" y="{y+off+len(body)*15+1}" text-anchor="middle" font-size="11" fill="#555" font-style="italic">{tag}</text>')
def ep(c,t):
    dx,dy=t[0]-c[0],t[1]-c[1]
    k=1/math.sqrt((dx/RX)**2+(dy/RY)**2)
    return (c[0]+k*dx,c[1]+k*dy)
def actor(x,y,label,stereo=None):
    out.append(f'<circle cx="{x}" cy="{y}" r="13" fill="#f6f6f6" stroke="#222" stroke-width="1.4"/>')
    out.append(f'<path d="M{x} {y+13}V{y+48}M{x-24} {y+26}H{x+24}M{x} {y+48}L{x-20} {y+78}M{x} {y+48}L{x+20} {y+78}" stroke="#222" stroke-width="1.4" fill="none"/>')
    for i,l in enumerate(label.split("\n")):
        out.append(f'<text x="{x}" y="{y+96+i*16}" text-anchor="middle" font-size="14">{l}</text>')
    if stereo:
        out.append(f'<text x="{x}" y="{y-24}" text-anchor="middle" font-size="12" font-style="italic">«{stereo}»</text>')
def assoc(a,b):
    out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#222" stroke-width="1.3"/>')
def dashed(a,b,label,lx=0,ly=0):
    out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#222" stroke-width="1.3" stroke-dasharray="7 5" marker-end="url(#open)"/>')
    mx,my=(a[0]+b[0])/2+lx,(a[1]+b[1])/2+ly
    out.append(f'<rect x="{mx-34:.1f}" y="{my-9:.1f}" width="68" height="16" fill="#fff"/>')
    out.append(f'<text x="{mx:.1f}" y="{my+4:.1f}" text-anchor="middle" font-size="12">{label}</text>')
def gen(a,b):
    out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#222" stroke-width="1.3" marker-end="url(#tri)"/>')

# use-case centres
XA,XB=580,950
C={ 'dash':(XA,100),'submit':(XA,180),'risk':(XA,305),'gen':(XA,405),'accept':(XA,505),'update':(XA,605),
    'rec':(XA,700),'ask':(XA,790),'triage':(XA,900),'ack':(XA,975),'audit':(XA,1050),'login':(XA,1120-45+0)}
C['login']=(XA,1050+75-0)
H=1200
L={'dash':'View Public\nRisk Dashboard\n(NFR-01)','submit':'Submit Citizen\nReport\n(FR-01)','gen':'Generate AI\nCAP Draft\n(FR-06)','risk':'Run Risk\nScoring\n(FR-04)',
   'accept':'Accept CAP\nDraft Item\n(FR-07)','update':'Update CAP\nStatus\n(FR-03)','rec':'View AI\nRecommendations\n(FR-05)','ask':'Ask AI\nQuestion\n(FR-08, FR-09)',
   'triage':'Triage Citizen\nReport\n(FR-02)','ack':'Acknowledge\nAlert\n(NFR-04)','audit':'View Audit Log\n(NFR-04)','login':'Log In\n(NFR-04)'}
B={'alert':(XB,235),'nl':(XB,745),'rag':(XB,835)}
LB={'alert':'Raise Alert\n(FR-10)','nl':'Ask NL\nData Query\n(FR-08)','rag':'Ask Regulatory\nQuestion (RAG)\n(FR-09)'}

out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append('<defs><marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M1 1L9 5L1 9" fill="none" stroke="#222" stroke-width="1.4"/></marker>'
           '<marker id="tri" viewBox="0 0 14 12" refX="13" refY="6" markerWidth="14" markerHeight="12" orient="auto"><path d="M1 1L13 6L1 11Z" fill="#fff" stroke="#222" stroke-width="1.4"/></marker></defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
out.append(f'<text x="{W/2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">HydroSentinel: Use-Case Diagram</text>')
out.append(f'<rect x="390" y="55" width="760" height="{H-80}" fill="#fcfcfc" stroke="#222" stroke-width="1.6" rx="4"/>')
out.append('<text x="770" y="80" text-anchor="middle" font-size="15" font-weight="bold">HydroSentinel System Boundary</text>')

ADM=(120,600); CIT=(120,140)
AIA=(1300,600); DWS=(1300,330)
# associations first (under ellipses)
for k in ['gen','risk','accept','update','rec','ask','triage','ack','audit','login']:
    assoc((ADM[0]+24,ADM[1]+26),(C[k][0]-RX,C[k][1]))
for k in ['dash','submit']:
    assoc((CIT[0]+24,CIT[1]+26),(C[k][0]-RX,C[k][1]))
assoc((AIA[0]-24,AIA[1]+26),ep(C['gen'],(AIA[0]-24,AIA[1]+26)))
assoc((AIA[0]-24,AIA[1]+26),ep(C['risk'],(AIA[0]-24,AIA[1]+26)))
assoc((AIA[0]-24,AIA[1]+26),ep(C['rec'],(AIA[0]-24,AIA[1]+26)))
assoc((AIA[0]-24,AIA[1]+26),ep(B['nl'],(AIA[0]-24,AIA[1]+26)))
assoc((AIA[0]-24,AIA[1]+26),ep(B['rag'],(AIA[0]-24,AIA[1]+26)))
assoc((DWS[0]-24,DWS[1]+26),ep(C['risk'],(DWS[0]-24,DWS[1]+26)))
# include / extend / generalisation
dashed(ep(C['gen'],C['risk']),ep(C['risk'],C['gen']),'«include»',-52,0)
dashed(ep(C['accept'],C['update']),ep(C['update'],C['accept']),'«include»',-52,0)
dashed(ep(B['alert'],C['submit']),ep(C['submit'],B['alert']),'«extend»',0,-4)
dashed(ep(B['alert'],C['risk']),ep(C['risk'],B['alert']),'«extend»',0,12)
gen(ep(B['nl'],C['ask']),ep(C['ask'],B['nl']))
gen(ep(B['rag'],C['ask']),ep(C['ask'],B['rag']))
for k,c in C.items(): ell(c,L[k])
for k,c in B.items(): ell(c,LB[k])
actor(*ADM,'Admin'); actor(*CIT,'Citizen')
actor(*AIA,'AI Engine\n(XGBoost + GPT-4o)','supporting'); actor(*DWS,'DWS Regulatory\nData','supporting')

out.append('</svg>')
open('4.1-use-case.svg','w').write('\n'.join(out))
