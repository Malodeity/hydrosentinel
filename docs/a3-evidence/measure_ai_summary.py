import json,time,urllib.request
A="http://127.0.0.1:8010"
def call(path,tok=None,method="GET",data=None):
    r=urllib.request.Request(A+path,method=method,data=(json.dumps(data).encode() if data else None))
    if tok: r.add_header("Authorization","Bearer "+tok)
    if data: r.add_header("Content-Type","application/json")
    t=time.perf_counter(); x=urllib.request.urlopen(r,timeout=60); b=x.read(); return x.status,time.perf_counter()-t,json.loads(b)
tok=call("/auth/login",method="POST",data={"email":"admin@hydrosentinel.co.za","password":"admin123"})[2]["access_token"]
ws=call("/wsa")[2]
pick=[w for w in ws if w["blue_drop_score"] is not None][:3]
for w in pick:
    c,t,j=call(f"/ai/wsa/{w['id']}/summary")
    txt=j["content"]; cites=str(round(w["blue_drop_score"],1)).rstrip("0").rstrip(".") in txt or str(int(w["blue_drop_score"])) in txt
    print("%d %.2fs | %s | Blue Drop %.1f | mentions score: %s | %d chars"%(c,t,w["name"][:26],w["blue_drop_score"],cites,len(txt)))
