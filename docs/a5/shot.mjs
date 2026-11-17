// Takes demo screenshots of the running app with headless Chrome (no extra install): node shot.mjs
// Needs the app on :5173 and :8000 in the demo state (bash reset_demo.sh).  Writes docs/a5/screens/*.png
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
const require = createRequire(os.homedir() + "/Library/Caches/hydrosentinel-dev/fe/package.json");
const WebSocket = require("ws");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = decodeURIComponent(new URL("./screens/", import.meta.url).pathname);
const API = "http://localhost:8000", APP = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const login = async (email, password) => (await fetch(API + "/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email, password }) })).json();
const admin = await login("admin@hydrosentinel.co.za", "admin123");
const contractors = await (await fetch(API + "/contractors", { headers: { authorization: "Bearer " + admin.access_token } })).json();
const users = await (await fetch(API + "/users", { headers: { authorization: "Bearer " + admin.access_token } })).json();
const withTickets = await (await fetch(API + "/assignments", { headers: { authorization: "Bearer " + admin.access_token } })).json();
const busy = withTickets.find((t) => t.status === "accepted" || t.status === "in_progress") ?? withTickets[0];
const cUser = users.find((u) => u.contractor_id === busy.contractor_id);
const contractor = await login(cUser.email, "contractor123");

const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=9333", "--window-size=1500,1000", "--hide-scrollbars", "--user-data-dir=/tmp/hs-shot-profile", "about:blank"], { stdio: "ignore" });
await sleep(2500);
const targets = await (await fetch("http://localhost:9333/json")).json();
const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.on("open", r));
let id = 0; const pending = new Map();
ws.on("message", (m) => { const d = JSON.parse(m); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } });
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const run = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 1000, deviceScaleFactor: 1.5, mobile: false });

async function open(path, session) {
  await send("Page.navigate", { url: APP + "/login" }); await sleep(1500);
  await run(`localStorage.clear()`);
  if (session) await run(`localStorage.setItem("hydrosentinel_token", ${JSON.stringify(session.access_token)}); localStorage.setItem("hydrosentinel_refresh_token", ${JSON.stringify(session.refresh_token)}); localStorage.setItem("hydrosentinel_user", ${JSON.stringify(JSON.stringify(session.user))});`);
  await send("Page.navigate", { url: APP + path }); await sleep(3500);
}
const clickText = (text, sel = "button,[role=tab],summary,a") => run(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(sel)})].find(e => e.textContent.trim().startsWith(${JSON.stringify(text)})); if (el) { el.click(); return true } return false })()`);
async function snap(name, full = false) {
  let params = { format: "png" };
  if (full) { const h = await run("document.documentElement.scrollHeight"); await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: Math.min(h, 2600), deviceScaleFactor: 1.5, mobile: false }); await sleep(500); }
  const r = await send("Page.captureScreenshot", params);
  writeFileSync(OUT + name + ".png", Buffer.from(r.result.data, "base64"));
  await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 1000, deviceScaleFactor: 1.5, mobile: false });
  console.log("saved", name);
}

await open("/", null); await snap("01-dashboard");
await open("/reports", null); await snap("02-report-form");
await open("/login", null); await snap("03-login");
await open("/admin", admin); await clickText("Citizen reports", "[role=tab]"); await sleep(1500); await snap("04-admin-reports", true);
await run(`(() => { const row = [...document.querySelectorAll("tr")].find(r => r.textContent.includes("Tembisa")); if (row) row.click(); })()`); await sleep(1200);
await snap("05-admin-report-open", true);
await open("/admin", admin); await clickText("Contractors", "[role=tab]"); await sleep(2000); await snap("06-contractors", true);
await open("/tickets", contractor); await snap("07-contractor-tickets", true);
await open("/admin", admin); await clickText("Audit log", "[role=tab]"); await sleep(1500); await snap("08-audit-log", true);
await open("/admin", admin); await clickText("CAP management", "[role=tab]"); await sleep(2000);
await run(`(() => { const row = [...document.querySelectorAll("tbody tr")].find(r => r.textContent.includes("Ekurhuleni")) || document.querySelector("tbody tr"); row && row.click(); })()`); await sleep(1500);
console.log("score button:", await clickText("Score risk now")); await sleep(2500);
console.log("score result:", await run(`document.querySelector('[role=status]')?.textContent`));
await snap("09-score-risk", true);
ws.close(); chrome.kill();
