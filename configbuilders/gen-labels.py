#!/usr/bin/env python

# requires https://code.google.com/p/pyfpdf/

# First generate all the switch "configs" but force the "labels.j2" template:
# ./gen-switch.py  --generate --template labels
# Then generate the labels:
# ./gen-labels.py


import os
from fpdf import FPDF
 
pdf = FPDF(orientation='P', unit='mm', format='A4')

leftmargin = 4.75
rightmargin = 4.75
topmargin = 6

pdf.set_margins(leftmargin, topmargin, rightmargin)
pdf.set_auto_page_break(False)
 
rows=5
cols=2
cellwidth=99
cellheight=57
cellgapx=2.5
cellgapy=0
 
col = -1
row = 0
debug = False

pdf.add_page()

files = os.listdir("out/switches/")
files.sort()

for file in files:
  if os.path.islink("out/switches/" + file) or file.endswith("~"):
    continue
  with open("out/switches/" + file, "r") as f:
    label = f.read().strip()

  label = label.replace("TenGigabitEthernet", "Te")
  label = label.replace("GigabitEthernet", "Gi")
  label = label.replace("FastEthernet", "Fa")
  label = label.replace("Ethernet", "Eth")

  col += 1
  if (col >= cols):
    pdf.ln()
    col = 0
    row += 1
    if (row >= rows):
      pdf.add_page()
      row = 0

  cellx = leftmargin + (col * (cellwidth + cellgapx))
  celly = topmargin + (row * (cellheight + cellgapy))

  pdf.set_font('Helvetica', '', 8.5)

  if debug:
    pdf.set_xy(cellx, celly)
    pdf.cell(cellwidth, cellheight, "", border=1, align="C")

  lineheight = 3.4
  height = len(label.split("\n")) * lineheight
  top = celly + ((lineheight + cellheight - height) / 2)
#celly + 6

  n = 0
  for line in label.split("\n"):
    if n == 0:
      pdf.set_text_color(0, 0, 192)
      pdf.set_font('', 'B', 14)
    else:
      pdf.set_font('', '', 9)

    if "Uplink" in line:
      pdf.set_text_color(0, 90, 0)
    elif "Downlink" in line:
      pdf.set_text_color(128, 0, 0)
    elif n > 0:
      pdf.set_text_color(0, 0, 0)
    pdf.set_xy(cellx + 25, top + (n*lineheight))
    pdf.write(0, txt=line)
    n += 1
        
#  pdf.multi_cell(cellwidth - 25, cellheight-10, "ABC\nDEF", 1, align="C")
  pdf.image('logo-label.png', cellx+3, celly+7, 15)
  pdf.image('nocnocnoc.png', cellx+cellwidth-8, celly+2, 4.45)

pdf.output('out/labels.pdf', 'F')

print "Created out/labels.pdf"
