#!/usr/bin/env python3

import time, serial, board, blynklib, blynktimer

# import busio
from digitalio import DigitalInOut, Direction
import adafruit_fingerprint

# FINGERPRINT SCANNER
#####################
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# If using with a computer such as Linux/RaspberryPi, Mac, Windows with USB/serial converter:
# import serial
uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)

# If using with Linux/Raspberry Pi and hardware UART:
# import serial
# uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)

# If using with Linux/Raspberry Pi 3 with pi3-disable-bt
# import serial
#uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)

finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# WEISS
#######
isSystemEnabled = False
isAccessGranted = False
weissVPINs = { "VPIN_ALARM": 0, "VPIN_FINGERPRINT_TERMINAL": 8, "VPIN_ENROLL_PRINT": 30, "VPIN_DELETE_PRINT": 31}

# SETUP
ipAddress = "192.168.0.5"
BLYNK_AUTH = "Qh9VT9rlG2Zlsrsy8TKS5crv01O7oaH8"
blynk = blynklib.Blynk(BLYNK_AUTH, server=ipAddress, port=8080)

# This block is equivalent to BLYNK_CONNECTED
@blynk.handle_event("connect")
def connect_handler():
    print("Connection Handler: Performing virtual pin synchronization.")
    for pin in list(weissVPINs.values()):
        blynk.virtual_sync(pin)
        blynk.read_response(timeout=0.5)
    print("Connection Handler: Completed virtual pin synchronization.")

# This is block is equivalent to BLYNK_WRITE(vPin)
@blynk.handle_event("write V{}".format(weissVPINs["VPIN_ALARM"]))
def write_handler(pin, value):
    global isSystemEnabled
    isSystemEnabled = bool(int(value[0]))

@blynk.handle_event("write V{}".format(weissVPINs["VPIN_ENROLL_PRINT"]))
def write_handler(pin, value):
    if finger.read_templates() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to read templates")
    #print("Fingerprint templates: ", finger.templates)
    if finger.count_templates() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to read templates")
    #print("Number of templates found: ", finger.template_count)
    if finger.read_sysparam() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to get system parameters")
    if int(value[0]) == 1:
        if finger.template_count == 0:
            if enroll_finger(0):
                print("Fingerprint Enroll Success.")
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Fingerprint Enroll Success\n")
            else:
                print("Fingerprint Enroll Fail.")
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Fingerprint Enroll Fail\n")
        else:
            print("Fingerprint already exists. Only one fingerprint can be enrolled at a time.")
            blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Fingerprint already exists. Only one fingerprint can be enrolled at a time.\n")


@blynk.handle_event("write V{}".format(weissVPINs["VPIN_DELETE_PRINT"]))
def write_handler(pin, value):
    if finger.read_templates() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to read templates")
    #print("Fingerprint templates: ", finger.templates)
    if finger.count_templates() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to read templates")
    #print("Number of templates found: ", finger.template_count)
    if finger.read_sysparam() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to get system parameters")
    if int(value[0]) == 1:
        if finger.template_count > 0:
            if finger.delete_model(0) == adafruit_fingerprint.OK:
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Fingerprint deleted!\n")
                print("Fingerprint deleted!")
            else:
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Failed to delete fingerpint\n")
                print("Failed to delete fingerprint!")
        else:
            blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "No fingerprint to delete.\n")
            print("No fingerpint to delete.")


##################################################


def get_fingerprint():
    """Get a finger print image, template it, and see if it matches!"""
    print("Waiting for image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        return False
    print("Searching...")
    if finger.finger_search() != adafruit_fingerprint.OK:
        return False
    return True


# pylint: disable=too-many-branches
def get_fingerprint_detail():
    """Get a finger print image, template it, and see if it matches!
    This time, print out each error instead of just returning on failure"""
    print("Getting image...", end="", flush=True)
    i = finger.get_image()
    if i == adafruit_fingerprint.OK:
        print("Image taken")
    else:
        if i == adafruit_fingerprint.NOFINGER:
            print("No finger detected")
        elif i == adafruit_fingerprint.IMAGEFAIL:
            print("Imaging error")
        else:
            print("Other error")
        return False

    print("Templating...", end="", flush=True)
    i = finger.image_2_tz(1)
    if i == adafruit_fingerprint.OK:
        print("Templated")
    else:
        if i == adafruit_fingerprint.IMAGEMESS:
            print("Image too messy")
        elif i == adafruit_fingerprint.FEATUREFAIL:
            print("Could not identify features")
        elif i == adafruit_fingerprint.INVALIDIMAGE:
            print("Image invalid")
        else:
            print("Other error")
        return False

    print("Searching...", end="", flush=True)
    i = finger.finger_fast_search()
    # pylint: disable=no-else-return
    # This block needs to be refactored when it can be tested.
    if i == adafruit_fingerprint.OK:
        print("Found fingerprint!")
        return True
    else:
        if i == adafruit_fingerprint.NOTFOUND:
            print("No match found")
        else:
            print("Other error")
        return False


# pylint: disable=too-many-statements
def enroll_finger(location):
    """Take a 2 finger images and template it, then store in 'location'"""
    count = 0
    countLimit = 100 # in milliseconds
    for fingerimg in range(1, 3):
        if fingerimg == 1:
            print("Place finger on sensor...", end="", flush=True)
            blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Place finger on sensor...")
        else:
            print("Place same finger again...", end="", flush=True)
            blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Place same finger again...")

        while True:
            if count >= countLimit:
                print("\n{} seconds timeout. Cancelling enrollment.".format(countLimit/10))
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "\n{} seconds timeout. Cancelling enrollment.\n".format(countLimit/10))
                return False
            i = finger.get_image()
            if i == adafruit_fingerprint.OK:
                print("Image taken")
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Image taken\n")
                count = 0
                break
            if i == adafruit_fingerprint.NOFINGER:
                count += 1
                time.sleep(0.1)
            elif i == adafruit_fingerprint.IMAGEFAIL:
                print("Imaging error")
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Imaging error\n")
                return False
            else:
                print("Other error")
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Other error\n")
                return False

        #print("Templating...", end="", flush=True)
        #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Templating...")
        i = finger.image_2_tz(fingerimg)
        if i == adafruit_fingerprint.OK:
            pass
            #print("Templated")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Templated\n")
        else:
            if i == adafruit_fingerprint.IMAGEMESS:
                pass
                #print("Image too messy")
                #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Image too messy\n")
            elif i == adafruit_fingerprint.FEATUREFAIL:
                pass
                #print("Could not identify features")
                #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Could not identify features\n")
            elif i == adafruit_fingerprint.INVALIDIMAGE:
                pass
                #print("Image invalid")
                #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Image invalid\n")
            else:
                pass
                #print("Other error")
                #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Other error\n")
            return False

        if fingerimg == 1:
            print("Remove finger")
            blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Remove finger\n")
            time.sleep(1)
            while i != adafruit_fingerprint.NOFINGER:
                i = finger.get_image()

    #print("Creating model...", end="", flush=True)
    #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Creating model...")
    i = finger.create_model()
    if i == adafruit_fingerprint.OK:
        pass
        #print("Created")
        #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Created\n")
    else:
        if i == adafruit_fingerprint.ENROLLMISMATCH:
            pass
            #print("Prints did not match")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Prints did not match\n")
        else:
            pass
            #print("Other error")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Other error\n")
        return False

    #print("Storing model #%d..." % location, end="", flush=True)
    #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Storing model #{}...".format(location))
    i = finger.store_model(location)
    if i == adafruit_fingerprint.OK:
        pass
        #print("Stored")
        #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Stored\n")
    else:
        if i == adafruit_fingerprint.BADLOCATION:
            pass
            #print("Bad storage location")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Bad storage location\n")
        elif i == adafruit_fingerprint.FLASHERR:
            pass
            #print("Flash storage error")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Flash storage error\n")
        else:
            pass
            #print("Other error")
            #blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Other error\n")
        return False

    return True


def save_fingerprint_image(filename):
    """Scan fingerprint then save image to filename."""
    while finger.get_image():
        pass

    # let PIL take care of the image headers and file structure
    from PIL import Image  # pylint: disable=import-outside-toplevel

    img = Image.new("L", (256, 288), "white")
    pixeldata = img.load()
    mask = 0b00001111
    result = finger.get_fpdata(sensorbuffer="image")

    # this block "unpacks" the data received from the fingerprint
    #   module then copies the image data to the image placeholder "img"
    #   pixel by pixel.  please refer to section 4.2.1 of the manual for
    #   more details.  thanks to Bastian Raschke and Danylo Esterman.
    # pylint: disable=invalid-name
    x = 0
    # pylint: disable=invalid-name
    y = 0
    # pylint: disable=consider-using-enumerate
    for i in range(len(result)):
        pixeldata[x, y] = (int(result[i]) >> 4) * 17
        x += 1
        pixeldata[x, y] = (int(result[i]) & mask) * 17
        if x == 255:
            x = 0
            y += 1
        else:
            x += 1

    if not img.save(filename):
        return True
    return False


##################################################


def get_num(max_number):
    """Use input() to get a valid number from 0 to the maximum size
    of the library. Retry till success!"""
    i = -1
    while (i > max_number - 1) or (i < 0):
        try:
            i = int(input("Enter ID # from 0-{}: ".format(max_number - 1)))
        except ValueError:
            pass
    return i

# Create timer dispatcher instance
timer = blynktimer.Timer()

@timer.register(interval=0.1)
def fingerprint_run():
    # Keep scanning for a fingerprint
    # If the finger is on a sensor, scan and look for a match.
    # If match is found, deactivate system
    if finger.get_image() == adafruit_fingerprint.OK:
        blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Processing fingerprint... ")
        if finger.image_2_tz(1) == adafruit_fingerprint.OK:
            if finger.finger_search() == adafruit_fingerprint.OK:
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "ACCESS GRANTED.\n")
                blynk.virtual_write(weissVPINs["VPIN_ALARM"], int(not isSystemEnabled))
                blynk.virtual_sync(weissVPINs["VPIN_ALARM"])
            else:
                blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "ACCESS DENIED.\n")

        #if finger.image_2_tz(1) != adafruit_fingerprint.NOFINGER:
        #    blynk.virtual_write(weissVPINs["VPIN_FINGERPRINT_TERMINAL"], "Remove finger\n")
        #    f = finger.get_image()
        #    while f != adafruit_fingerprint.NOFINGER:
        #        f = finger.get_image()


while True:
    blynk.run()
    timer.run()
