#!/bin/bash

for i in /var/lib/rancid/emfcamp/configs/*.emf.camp; do
    j=`basename $i`
# remove serial numbers, passwords, and crypto sections
    cat $i | sed 's/\(secret \|Serial Number: \|serial number \|serial \|SN: \|Processor ID: \|encrypted \).*$/\1REDACTED/g' | sed 's/community [^ ]*/community REDACTED/g' | sed 's/REDACTED name [^ ]*/REDACTED name REDACTED/g' | awk '/^!/{off=0}/^crypto /{off=1} {if(off==0) {print}}' > ../archives/2014/deviceconfigs/$j
done
