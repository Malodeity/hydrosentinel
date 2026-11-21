#!/bin/bash
# Rebuilds every UML picture. Needs java, graphviz (dot), Google Chrome and plantuml.jar (set PLANTUML_JAR). Run from anywhere.
#   PLANTUML_JAR=/path/to/plantuml.jar bash docs/a5/uml/build_uml.sh
cd "$(dirname "$0")" || exit 1
export PLANTUML_LIMIT_SIZE=16384 PATH=/opt/homebrew/bin:$PATH
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
( cd ../../../backend && PYTHONPATH=. python3 ../docs/a5/uml/gen_class.py && PYTHONPATH=. python3 ../docs/a5/uml/gen_class_picture.py )   # class .puml and the picture, both read from models.py
for f in ISJ107V_A5_Q3.3_Sequence ISJ107V_A5_Q3.3b_Activity ISJ107V_A5_Q3.4b_Deployment; do
  for t in png svg; do java -Djava.awt.headless=true -jar "$PLANTUML_JAR" -t$t $f.puml; done
done
python3 gen_usecase.py; python3 gen_component.py                                                       # drawn in the same layout as Assignment 4
for f in ISJ107V_A5_Q3.1_UseCase ISJ107V_A5_Q3.2_Class ISJ107V_A5_Q3.4a_Component; do
  W=$(grep -o 'width="[0-9]*"' $f.svg | head -1 | tr -dc 0-9); H=$(grep -o 'height="[0-9]*"' $f.svg | head -1 | tr -dc 0-9)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=$W,$H --screenshot="$PWD/$f.png" "file://$PWD/$f.svg"
done
