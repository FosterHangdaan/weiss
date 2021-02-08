#!/usr/bin/env python3

import blynklib, blynktimer
import datetime as dt
import calendar as cal

isSystemEnabled = False
isSchedulerEnabled = False
weissVPINs = { "VPIN_ALARM": 0 }
weekdayVPINs = { "Monday": 10, "Tuesday": 11, "Wednesday": 12, "Thursday": 13, "Friday": 14, "Saturday": 15, "Sunday": 16 }
timerangeVPINs = { "Monday": 20, "Tuesday": 21, "Wednesday": 22, "Thursday": 23, "Friday": 24, "Saturday": 25, "Sunday": 26 }
schedule =  {
                "Monday": [False, dt.time(0), dt.time(0)],          # [Enable, Start time, Stop Time]
                "Tuesday": [False, dt.time(0), dt.time(0)],
                "Wednesday": [False, dt.time(0), dt.time(0)],
                "Thursday": [False, dt.time(0), dt.time(0)],
                "Friday": [False, dt.time(0), dt.time(0)],
                "Saturday": [False, dt.time(0), dt.time(0)],
                "Sunday": [False, dt.time(0), dt.time(0)]
            }

# My functions
def getKeyOf(someValue, inDictionary):
	return list(inDictionary.keys())[list(inDictionary.values()).index(someValue)]

# SETUP
ipAddress = "192.168.0.0"
BLYNK_AUTH = "Qh9VT9rlG2Zlsrsy8TKS5crv01O7oaH8"
blynk = blynklib.Blynk(BLYNK_AUTH, server=ipAddress, port=8080)


# This block is equivalent to BLYNK_CONNECTED
@blynk.handle_event("connect")
def connect_handler():
    print("Connection Handler: Performing virtual pin synchronization.")
    for pin in (list(weissVPINs.values()) + list(weekdayVPINs.values()) + list(timerangeVPINs.values())):
        blynk.virtual_sync(pin)
        blynk.read_response(timeout=0.5)
    print("Connection Handler: Completed virtual pin synchronization.")

# This is block is equivalent to BLYNK_WRITE(vPin)
@blynk.handle_event("write V*" )
def write_handler(pin, value):
    global isSystemEnabled
    global isSchedulerEnabled
    if pin in weekdayVPINs.values():
        day = getKeyOf(pin, weekdayVPINs)
        schedule[day][0] = bool(int(value[0]))
    if pin in timerangeVPINs.values():
        day = getKeyOf(pin, timerangeVPINs)

        if value[0] != '':
            start = dt.time(hour=int(value[0])//3600, minute=(int(value[0])//60)%60)
        else:
            start = dt.time(0)

        if value[1] != '':
            stop = dt.time(hour=int(value[1])//3600, minute=(int(value[1])//60)%60)
        else:
            stop = dt.time(0)
        schedule[day][1] = start
        schedule[day][2] = stop
    if pin == weissVPINs["VPIN_ALARM"]:
        isSystemEnabled = bool(int(value[0]))

# Create timer dispatcher instance
timer = blynktimer.Timer()

@timer.register(interval=1)
def scheduler():
    now = dt.datetime.now()
    weekday = cal.day_name[now.today().weekday()]
    isWeekdayEnabled = schedule[weekday][0]
    startTime = schedule[weekday][1]
    stopTime = schedule[weekday][2]

    if isWeekdayEnabled:
        if now.time() > startTime and now.time() < stopTime:
            blynk.virtual_write(weissVPINs["VPIN_ALARM"], 1)
        else:
            blynk.virtual_write(weissVPINs["VPIN_ALARM"], 0)
        blynk.virtual_sync(weissVPINs["VPIN_ALARM"])

while True:
    blynk.run()
    timer.run()
