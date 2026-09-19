import json, time, urllib.request, urllib.error
def call(base,path,token=None,method="GET",data=None,timeout=60):
    req=urllib.request.Request(base+path,method=method,data=(json.dumps(data).encode() if data is not None else None))
    if token: req.add_header("Authorization","Bearer "+token)
    if data is not None: req.add_header("Content-Type","application/json")
    t=time.perf_counter()
    try: r=urllib.request.urlopen(req,timeout=timeout); c=r.status; b=r.read()
    except urllib.error.HTTPError as e: c=e.code; b=e.read()
    return c,time.perf_counter()-t,b
def login(base):
    c,_,b=call(base,"/auth/login",method="POST",data={"email":"admin@hydrosentinel.co.za","password":"admin123"}); return json.loads(b)["access_token"]
A="http://127.0.0.1:8010"; N="http://127.0.0.1:8011"
tok=login(A)
qs=["How many WSAs are high risk in each province?","Which Eastern Cape WSAs have no CAP and are high risk?","Compare the average Blue Drop score of Gauteng and Western Cape."]
print("--- AI-NFR-02 query agent (real GPT-4o) ---")
for q in qs:
    c,t,b=call(A,"/ai/query",tok,"POST",{"question":q},timeout=90)
    try: j=json.loads(b); calls=len(j["tool_calls"]); ans=j["answer"][:110].replace("\n"," ")
    except Exception: calls=-1; ans=b[:100]
    print("%d in %.2fs, tool_calls=%d | Q: %s | A: %s"%(c,t,calls,q[:48],ans))
print("--- NFR-02 with OpenAI key blank (port 8011) ---")
tn=login(N)
c,t,b=call(N,"/wsa"); print("core GET /wsa ->",c,"%.3fs"%t)
c,t,b=call(N,"/wsa?x=1"); 
wsas=json.loads(call(N,"/wsa")[2]); wid=wsas[0]["id"]
for path in [f"/ai/wsa/{wid}/summary",f"/ai/wsa/{wid}/cap-draft","/ai/digest"]:
    c,t,b=call(N,path,tn if "cap-draft" in path else None); print("AI",path[:34],"->",c,b[:70].decode(),"%.3fs"%t)
c,t,b=call(N,"/alerts",tn); print("core GET /alerts ->",c)
c,t,b=call(N,"/risk/scores"); print("core GET /risk/scores ->",c)
