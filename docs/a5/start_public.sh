#!/usr/bin/env bash
# Runs the demo and puts it on ONE public ngrok URL (app + API together).
#   bash docs/a5/start_public.sh        start, print the URL
#   bash docs/a5/start_public.sh stop   stop the public tunnel and its Vite
# The local demo on :5173 / :8000 is not touched. Use the :5173 address as the offline fallback.
REPO="/Users/malo/Documents/New project/hydrosentinel"
ENV_DIR="$HOME/Library/Caches/hydrosentinel-dev"
if [ "$1" = "stop" ]; then pkill -f "ngrok http 5174"; pkill -f "vite --port 5174"; echo stopped; exit 0; fi

bash "$REPO/docs/a4/start_demo.sh" || exit 1          # database, API :8000, normal app :5173
cp "$REPO/frontend/vite.config.ts" "$ENV_DIR/fe/vite.config.ts"
cd "$ENV_DIR/fe" || exit 1
pkill -f "vite --port 5174" 2>/dev/null
# VITE_API_URL=/api makes the browser call the same address it loaded from; the proxy in vite.config.ts forwards it to :8000
VITE_API_URL=/api nohup npx vite --port 5174 --host localhost > "$ENV_DIR/vite_public.log" 2>&1 &
for i in $(seq 1 20); do curl -s -m2 -o /dev/null http://localhost:5174 && break; sleep 1; done
pkill -f "ngrok http 5174" 2>/dev/null
nohup ngrok http 5174 --log=stdout > "$ENV_DIR/ngrok.log" 2>&1 &
URL=""
for i in $(seq 1 20); do
  URL=$(curl -s -m2 http://localhost:4040/api/tunnels | python3 -c "import sys,json;print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null) && [ -n "$URL" ] && break
  sleep 1
done
if [ -z "$URL" ]; then echo "ngrok did not start. See: tail $ENV_DIR/ngrok.log"; exit 1; fi
echo; echo "PUBLIC URL: $URL"
echo "API check:  $(curl -s -m5 -o /dev/null -w '%{http_code}' -H 'ngrok-skip-browser-warning: 1' "$URL/api/wsa")  (want 200)"
echo "Anyone with this link can reach the demo, including the sign-in page. Change the admin password first (key icon in the header)."
echo "Stop it with: bash docs/a5/start_public.sh stop"
