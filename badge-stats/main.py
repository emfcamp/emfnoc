# EMF NOC Stats badge app by davidc
# License: CC0

import ugfx, time, wifi, sys, onboard

import usocket, ujson
from imu import IMU

def cls():
    ugfx.area(0, 0, 320, 240, ugfx.BLACK)
    c.hide()
    c.show()

print("Stats app starting")

# Initialise graphics

print("Init uGFX")

ugfx.init()
ugfx.area(0, 0, ugfx.width(), ugfx.height(), ugfx.BLACK)
ugfx.set_default_font(ugfx.FONT_TITLE)

# Set up all the styles

print("Init Styles")

sty = ugfx.Style()
sty.set_enabled([ugfx.PURPLE, ugfx.BLACK, ugfx.GREEN, ugfx.GREY])
sty.background(ugfx.BLACK)

styUse = ugfx.Style()
styUse.set_enabled([ugfx.PURPLE, ugfx.BLACK, ugfx.GREEN, ugfx.GREY])
styUse.background(ugfx.BLACK)

styLbl = ugfx.Style()
styLbl.set_enabled([0xdddddd, ugfx.BLACK, ugfx.GREEN, ugfx.GREY])
styLbl.background(ugfx.BLACK)

styVal = ugfx.Style()
styVal.set_enabled([ugfx.WHITE, ugfx.BLACK, ugfx.GREEN, ugfx.GREY])
styVal.background(ugfx.BLACK)

# Root container
c = ugfx.Container(0, 0, ugfx.width(), ugfx.height(), style=sty)

# Connect to Wifi

print("Init Wifi")
cls()
ugfx.text(0, 0, "WIFI-CONNECT", ugfx.WHITE)

while True:
    try:
        wifi.connect()
    except Exception as e:
        sys.print_exception(e)
        cls()
        ugfx.text(0, 0, "WIFI-TRYAGAIN", ugfx.WHITE)
        continue
    break

# Set up display
# NB: RIGHTTOP and CENTERTOP are reversed

ugfx.set_default_font(ugfx.FONT_NAME)
ugfx.Label(0, 0, ugfx.width(), ugfx.height(), "use moar bandwidth!", justification=ugfx.Label.RIGHTTOP, style=styUse, parent=c)

ugfx.set_default_font(ugfx.FONT_TITLE)
ugfx.Label(0, 0+120, 50, 60, "In", justification=ugfx.Label.CENTER, style=styLbl, parent=c)

ugfx.set_default_font(ugfx.FONT_NAME)
curIn = ugfx.Label(55, 0+120, ugfx.width()-50, 60, "LOADING", justification=ugfx.Label.LEFT, style=styVal, parent=c)

ugfx.set_default_font(ugfx.FONT_TITLE)
ugfx.Label(0, 0+180, 50, 60, "Out", justification=ugfx.Label.CENTER, style=styLbl, parent=c)

sty.set_enabled([ugfx.WHITE, ugfx.BLACK, ugfx.GREEN, ugfx.GREY])
ugfx.set_default_font(ugfx.FONT_NAME)
curOut = ugfx.Label(55, 0+180, ugfx.width()-50, 60, "PLZWAIT", justification=ugfx.Label.LEFT, style=styVal, parent=c)

c.show()

# Unused, broadcast and multicasts are blocked on the wifi
#s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#s.bind(('', 14612))
#s.setblocking(True)

#while True:
#data, addr = s.recvfrom(1024)
#curOut.text(data)

imu = IMU()

connectto = usocket.getaddrinfo('monitor1.emf.camp',80)

oldorientation = ugfx.orientation()

looped = 0


def updateStats():
    # Download the JSON file
    s = usocket.socket()
    try:
        s.connect(connectto[0][4])

        s.send("GET /api/\r\n")
        output = s.recv(4096)
        s.close()
    except Exception as e:
        sys.print_exception(e)
        curIn.text("NET")
        curOut.text("GONE?")
        time.sleep(5)
        return

    # Decode the JSON
    print(output)
    try:
        data = ujson.loads(output)
    except Exception as e:
        sys.print_exception(e)
        curIn.text("JSON")
        curOut.text("ERROR")
        return

    # Update the display

    curIn.text("%.0f Mbps" % (data['uplink_in'] / 1000000))
    curOut.text("%.0f Mbps" % (data['uplink_out'] / 1000000))

# An X second delay, but checking the accelerometer every 1 second
def delayLoop(secs):
    global oldorientation
    for i in range(0, secs):
        print("miniloop")

        ival = imu.get_acceleration()
        if ival['y'] < 0:
            neworientation = 0
        else:
            neworientation = 180

        if neworientation != oldorientation:
            ugfx.orientation(neworientation)
            cls()
            oldorientation = neworientation
        time.sleep(1)

while True:
    print("loopy")

    updateStats()

    looped += 1
    if (looped > 120):
        print("REseTTING")
        onboard.semihard_reset()

    delayLoop(5)

