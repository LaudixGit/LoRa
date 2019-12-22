#!/usr/bin/env python

# https://create.arduino.cc/projecthub/aardweeno/controlling-an-arduino-from-a-pi3-using-i2c-59817b
# https://arduino.stackexchange.com/questions/47947/sending-a-string-from-rpi-to-arduino-working-code
# https://raspberrypi.stackexchange.com/questions/62206/sending-and-receiving-string-data-between-arduino-and-raspberry-pi-using-the-i2c
# https://buildmedia.readthedocs.org/media/pdf/smbus2/latest/smbus2.pdf
# https://stackoverflow.com/questions/32656722/python-can-i-read-two-bytes-in-one-transaction-with-the-smbus-module
# https://realpython.com/lessons/serializing-json-data/#:~:targetText=The%20json%20module%20exposes%20two,a%20string%20in%20JSON%20format.
# https://realpython.com/python-json/

from smbus import SMBus

addr = 0x8 # bus address
bus = SMBus(1) # indicates /dev/ic2-1

# commands I made up to send to arduino (matches commands in ino file)
commandReset = 0            #reboots the Arduino and the radio

def StringToBytes(val):
        retVal = []
        for c in val:
                retVal.append(ord(c))
        return retVal

#***** REBOOT the radio and Arduino
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandReset,StringToBytes(""))
print("Arduino rebooting. Hope it recovers")
smsMessage = ""
