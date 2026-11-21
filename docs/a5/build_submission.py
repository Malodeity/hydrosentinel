"""Builds the two PDFs for each document.
  public   (committed to git): the link, and "logins are in the submission note" in place of the passwords
  private  (docs/a5/submission_private/, NOT committed): the same documents with the real logins from .env.neon, for MyTUTor
Run:  python3 docs/a5/build_submission.py"""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
env = {}
for line in open(os.path.join(ROOT, ".env.neon")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); env[k] = v.strip('"')
modes = {
    "public": {"@@ADMIN_PW@@": "(given in the submission note)", "@@DEMO_PW@@": "(given in the submission note)",
               "@@ADMIN_LINE@@": "Password: in the submission note", "@@DEMO_LINE@@": "Password: in the submission note"},
    "private": {"@@ADMIN_PW@@": env["HOSTED_ADMIN_PASSWORD"], "@@DEMO_PW@@": env["HOSTED_DEMO_PASSWORD"],
                "@@ADMIN_LINE@@": "Password: <b>" + env["HOSTED_ADMIN_PASSWORD"] + "</b>", "@@DEMO_LINE@@": "Password: <b>" + env["HOSTED_DEMO_PASSWORD"] + "</b>"},
}
os.makedirs(os.path.join(HERE, "submission_private"), exist_ok=True)
subprocess.run(["bash", "-c", f"cat '{HERE}/../pdf.css' '{HERE}/../a4/report.css' > '{HERE}/report.css'"], check=True)
open(os.path.join(HERE, "report.css"), "a").write("\ntd code { white-space: nowrap; }\n")   # an email or a password must never wrap onto two lines
for mode, subs in modes.items():
    def fill(text):
        for k, v in subs.items(): text = text.replace(k, v)
        return text
    md = os.path.join(HERE, "_tmp_report.md"); html = os.path.join(HERE, "_tmp_report.html")
    open(md, "w").write(fill(open(os.path.join(HERE, "ISJ107V_Assignment5_213355813.md")).read()))
    subprocess.run(f"pandoc '{md}' -f gfm+raw_html -t html5 -s --metadata title='ISJ107V Assignment 5' -H <(echo \"<style>$(cat '{HERE}/report.css')</style>\") -B '{HERE}/cover.html' -o '{html}'", shell=True, executable="/bin/bash", check=True, cwd=HERE)
    out_report = os.path.join(HERE, "ISJ107V_Assignment5_213355813.pdf") if mode == "public" else os.path.join(HERE, "submission_private", "ISJ107V_Assignment5_213355813.pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_report}", f"file://{html}"], check=True, capture_output=True)
    sl = os.path.join(HERE, "slides", "_tmp_slides.html")
    open(sl, "w").write(fill(open(os.path.join(HERE, "slides", "slides.html")).read()))
    out_slides = os.path.join(HERE, "slides", "ISJ107V_A5_213355813_Slides.pdf") if mode == "public" else os.path.join(HERE, "submission_private", "ISJ107V_A5_213355813_Slides.pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_slides}", f"file://{sl}"], check=True, capture_output=True)
    for f in (md, html, sl): os.remove(f)
    print(mode, "built")
