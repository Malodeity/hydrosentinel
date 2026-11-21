"""A tiny mail server for the demonstration: it accepts every message on 127.0.0.1:1025 and prints it, so the audience can SEE the email a citizen
would receive. It delivers nothing anywhere. Started by start_mail_demo.sh.   python3 smtp_sink.py"""
import socketserver
import sys


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        send = lambda text: self.wfile.write((text + "\r\n").encode())
        send("220 sink ready")
        data, lines = False, []
        for raw in self.rfile:
            line = raw.decode(errors="replace").rstrip("\r\n")
            if data:
                if line == ".":
                    print("\n===== EMAIL RECEIVED =====\n" + "\n".join(lines) + "\n==========================", flush=True)
                    data, lines = False, []
                    send("250 queued")
                else:
                    lines.append(line[1:] if line.startswith("..") else line)
                continue
            cmd = line.upper()
            if cmd.startswith(("EHLO", "HELO")): send("250 sink")
            elif cmd.startswith(("MAIL", "RCPT", "RSET", "NOOP")): send("250 ok")
            elif cmd.startswith("DATA"): data = True; send("354 end with a dot")
            elif cmd.startswith("QUIT"): send("221 bye"); return
            else: send("500 what")


if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", 1025), Handler) as server:
        print("mail sink listening on 127.0.0.1:1025", flush=True)
        server.serve_forever()
