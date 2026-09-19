import json, statistics, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
B="http://127.0.0.1:8010"
def get(path, token=None, method="GET", data=None):
    req=urllib.request.Request(B+path, method=method, data=data)
    if token: req.add_header("Authorization","Bearer "+token)
    if data: req.add_header("Content-Type","application/json")
    t=time.perf_counter()
    try:
        r=urllib.request.urlopen(req,timeout=30); code=r.status; body=r.read()
    except urllib.error.HTTPError as e: code=e.code; body=e.read()
    return code,(time.perf_counter()-t),body
def pct(v,p): v=sorted(v); return v[min(len(v)-1,int(round(p/100*len(v)))-1)]
# NFR-01 sequential
seq=[get("/wsa")[1] for _ in range(100)]
print("NFR-01 sequential n=100 GET /wsa: median %.3fs p95 %.3fs max %.3fs"%(statistics.median(seq),pct(seq,95),max(seq)))
# NFR-01 50 concurrent users, 4 requests each
def worker(_): return [get("/wsa")[1] for _ in range(4)]
t0=time.perf_counter()
with ThreadPoolExecutor(50) as ex: res=[x for r in ex.map(worker,range(50)) for x in r]
print("NFR-01 concurrent 50 users x4 (n=%d): median %.3fs p95 %.3fs max %.3fs wall %.2fs"%(len(res),statistics.median(res),pct(res,95),max(res),time.perf_counter()-t0))
c,t,b=get("/wsa"); print("payload: %d WSAs, %d KB"%(len(json.loads(b)),len(b)//1024))
# NFR-04 unauthenticated
for path,method in [("/audit-log","GET"),("/alerts","GET"),("/risk/score/00000000-0000-0000-0000-000000000000","POST"),("/reports","GET"),("/users","GET")]:
    c,t,_=get(path,method=method, data=(b"{}" if method=="POST" else None))
    print("NFR-04 no token %s %s -> %d"%(method,path,c))
c,t,_=get("/wsa/00000000-0000-0000-0000-000000000000",method="PATCH",data=b'{"cap_status":"submitted"}'); print("NFR-04 no token PATCH /wsa/{id} ->",c)
# login admin (viewer role token check later)
c,t,b=get("/auth/login",method="POST",data=json.dumps({"email":"admin@hydrosentinel.co.za","password":"admin123"}).encode())
print("login ->",c)
tok=json.loads(b).get("access_token") if c==200 else None
open("/tmp/hs_token_ok","w").write(tok or "")
if tok:
    for path in ["/ai/wsa/00000000-0000-0000-0000-000000000000/summary","/ai/digest"]:
        c,t,b=get(path,token=tok); print("NFR-02 AI endpoint %s -> %d %s (%.2fs)"%(path,c,b[:90],t))
    c,t,_=get("/wsa",token=tok); print("core GET /wsa with AI unavailable -> %d (%.3fs)"%(c,t))
