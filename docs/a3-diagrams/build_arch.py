out=[]
def esc(s): return s.replace("&","&amp;").replace("<","&lt;")
def box(x,y,w,h,title,sub=None,fill="#f6f6f6",stroke="#222"):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    if sub:
        out.append(f'<text x="{x+w/2}" y="{y+h/2-4}" text-anchor="middle" font-size="14" font-weight="bold">{esc(title)}</text>')
        for i,l in enumerate(sub.split("\n")):
            out.append(f'<text x="{x+w/2}" y="{y+h/2+14+i*15}" text-anchor="middle" font-size="12">{esc(l)}</text>')
    else:
        out.append(f'<text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle" font-size="14" font-weight="bold">{esc(title)}</text>')
def band(y,h,label,fill):
    out.append(f'<rect x="30" y="{y}" width="1130" height="{h}" rx="10" fill="{fill}" stroke="#999" stroke-width="1" stroke-dasharray="5 4"/>')
    out.append(f'<text x="44" y="{y+20}" font-size="13" font-weight="bold" fill="#444">{esc(label)}</text>')
def arrow(x1,y1,x2,y2,label=None,lx=8,dash=False,both=False):
    d=' stroke-dasharray="6 4"' if dash else ''
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#222" stroke-width="1.6"{d} marker-end="url(#a)"' + (' marker-start="url(#as)"' if both else '') + '/>')
    if label:
        mx,my=(x1+x2)/2,(y1+y2)/2
        w=len(label)*6.6+8
        out.append(f'<rect x="{mx+lx-4}" y="{my-11}" width="{w}" height="17" fill="#fff"/>')
        out.append(f'<text x="{mx+lx}" y="{my+2}" font-size="12">{esc(label)}</text>')
W,H=1500,830
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M1 1L9 5L1 9z" fill="#222"/></marker><marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M9 1L1 5L9 9z" fill="#222"/></marker></defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
out.append(f'<text x="{W/2}" y="32" text-anchor="middle" font-size="19" font-weight="bold">HydroSentinel: High-Level System Architecture</text>')

band(56,100,"Users","#f4f4f4"); band(190,110,"Interfaces (React 18 single-page app)","#eef3fb")
band(335,120,"Services (FastAPI application server)","#eef7ee"); band(490,120,"AI component","#fdf1e3")
band(645,120,"Data stores","#f4f4f4")

box(180,86,300,56,"Citizen","reports issues, views public dashboard")
box(720,86,340,56,"Admin (municipal or oversight staff)","manages CAPs, triages reports, uses AI tools")
box(60,225,250,60,"Public Dashboard","risk map, digest, WSA card")
box(330,225,250,60,"Report Page","submit and track a report")
box(600,225,250,60,"Login Page","admin sign-in (JWT)")
box(870,225,270,60,"Admin Page","reports, CAP, alerts, AI assistant")
box(60,370,200,68,"Auth and Users","login, refresh, roles")
box(275,370,200,68,"WSA and Risk","list, CAP update, scoring")
box(490,370,200,68,"Reports and Alerts","intake, triage, alerts")
box(705,370,200,68,"Audit Log","immutable change record")
box(920,370,220,68,"AI Service","rate limited, admin only")
box(60,525,250,68,"Risk Predictor","XGBoost, heuristic fallback",fill="#fff8ee",stroke="#a4661a")
box(330,525,250,68,"RAG Index","TF-IDF over regulatory PDFs",fill="#fff8ee",stroke="#a4661a")
box(600,525,250,68,"Query Agent","GPT-4o plus 5 whitelisted data tools",fill="#fff8ee",stroke="#a4661a")
box(870,525,270,68,"CAP Drafter and Summaries","GPT-4o via one helper",fill="#fff8ee",stroke="#a4661a")
box(60,680,220,64,"Regulatory PDFs","data/raw")
box(300,680,200,64,"model.pkl","trained XGBoost")
box(520,680,220,64,"Photo uploads","data/uploads")
box(760,680,200,64,"PostgreSQL","8 tables, audit trail")
box(1000,680,140,64,"ETL scripts","offline batch")

box(1200,525,260,68,"OpenAI API","GPT-4o (external cloud)",fill="#e9eefb")
box(1200,660,260,50,"Municipal Money API",None,fill="#e9eefb")
box(1200,725,260,50,"DWS reports (PDF)",None,fill="#e9eefb")
out.append('<text x="1330" y="500" text-anchor="middle" font-size="13" font-weight="bold" fill="#444">External services</text>')

# users -> interfaces
arrow(330,142,185,225); arrow(330,142,455,225)
arrow(890,142,725,225); arrow(890,142,1005,225)
# interfaces -> services (single bundled arrow)
arrow(600,300,600,335,"REST / JSON over HTTPS",10,both=True)
# services -> AI
arrow(600,455,600,490,"in-process calls",10)
# AI -> data
arrow(600,610,600,645,"SQL and file reads",10)
# AI -> OpenAI
arrow(1140,559,1200,559,None)
out.append('<text x="1170" y="548" text-anchor="middle" font-size="11">HTTPS</text>')
# ETL
arrow(1140,712,1200,690,None); arrow(1140,725,1200,750,None)
arrow(1000,712,960,712)
out.append('</svg>')
open('A3-3.1-architecture.svg','w').write("\n".join(out))
