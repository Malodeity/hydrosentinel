#!/usr/bin/env bash
# Lets the audience see the citizen emails (FR-11). Starts a mail sink on port 1025 and restarts the backend pointing at it, then you watch the log:
#   bash docs/a5/start_mail_demo.sh        then in a second terminal tab:   tail -f ~/Library/Caches/hydrosentinel-dev/mail.log
# Nothing is sent to a real mailbox. Stop with: bash docs/a5/start_mail_demo.sh stop   (and start_demo.sh to get the normal backend back)
REPO="/Users/malo/Documents/New project/hydrosentinel"
ENV_DIR="$HOME/Library/Caches/hydrosentinel-dev"
pkill -f "docs/a5/smtp_sink.py" 2>/dev/null
if [ "$1" = "stop" ]; then pkill -f "uvicorn main:app --port 8000"; echo "mail sink stopped; run docs/a4/start_demo.sh for the normal backend"; exit 0; fi
nohup python3 "$REPO/docs/a5/smtp_sink.py" > "$ENV_DIR/mail.log" 2>&1 &
sleep 1
pkill -f "uvicorn main:app --port 8000"; sleep 2
export SMTP_HOST=127.0.0.1 SMTP_PORT=1025 SMTP_FROM="HydroSentinel <no-reply@hydrosentinel.co.za>"
bash "$REPO/docs/a4/start_demo.sh" | tail -2
echo "Watch the emails:  tail -f $ENV_DIR/mail.log"
