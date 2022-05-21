#!/bin/bash
# deploy mopup files to each switch via tftp

for j in out/switches/*.emf.camp; do
    i=`basename $j`
    clogin -c "conf t; file prompt quiet; exit; copy tftp://78.158.87.21/$i running-config; exit" $i
done
