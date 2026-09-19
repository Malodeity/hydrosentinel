import json,time,urllib.request
A="http://127.0.0.1:8010"
def call(path,tok=None,method="GET",data=None):
    r=urllib.request.Request(A+path,method=method,data=(json.dumps(data).encode() if data else None))
    if tok: r.add_header("Authorization","Bearer "+tok)
    if data: r.add_header("Content-Type","application/json")
    t=time.perf_counter(); x=urllib.request.urlopen(r,timeout=90); b=x.read(); return x.status,time.perf_counter()-t,json.loads(b)
tok=call("/auth/login",method="POST",data={"email":"admin@hydrosentinel.co.za","password":"admin123"})[2]["access_token"]
ws=[w for w in call("/wsa")[2] if w["blue_drop_score"] is not None][:3]
for w in ws:
    c,t,j=call(f"/ai/wsa/{w['id']}/cap-draft",tok)
    print("%d %.2fs | %s | %d items | priorities %s | days %s"%(c,t,w["name"][:24],len(j["items"]),[i["priority"] for i in j["items"]],[i["suggested_due_in_days"] for i in j["items"]]))
