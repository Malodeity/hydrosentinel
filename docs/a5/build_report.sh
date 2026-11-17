#!/bin/bash
# Rebuild the A5 written report PDF (needs pandoc and Google Chrome). Run from anywhere.
cd "$(dirname "$0")" || exit 1
cat ../pdf.css ../a4/report.css > report.css
pandoc ISJ107V_Assignment5_213355813.md -f gfm+raw_html -t html5 -s --metadata title="ISJ107V Assignment 5" -H <(echo "<style>$(cat report.css)</style>") -B cover.html -o build.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="ISJ107V_Assignment5_213355813.pdf" "file://$PWD/build.html"
rm -f build.html
