#!/usr/bin/env python

# https://create.arduino.cc/projecthub/aardweeno/controlling-an-arduino-from-a-pi3-using-i2c-59817b
# https://arduino.stackexchange.com/questions/47947/sending-a-string-from-rpi-to-arduino-working-code
# https://raspberrypi.stackexchange.com/questions/62206/sending-and-receiving-string-data-between-arduino-and-raspberry-pi-using-the-i2c
# https://buildmedia.readthedocs.org/media/pdf/smbus2/latest/smbus2.pdf
# https://stackoverflow.com/questions/32656722/python-can-i-read-two-bytes-in-one-transaction-with-the-smbus-module

from smbus import SMBus
import time

addr = 0x8 # bus address
bus = SMBus(1) # indicates /dev/ic2-1
#bus.write_byte(addr, 0x1) # switch it on

def writeData(value):
    byteValue = StringToBytes(value)    
    bus.write_i2c_block_data(addr,0x00,byteValue) #first byte is 0=command byte.. just is.
    return -1


def StringToBytes(val):
        retVal = []
        for c in val:
                retVal.append(ord(c))
        return retVal

print("sending")
writeData("test as much as I can")   
time.sleep(1)

while 1:
    try:
        # data = bus.read_byte(addr)
        # print('data {}'.format(data))
        #global smsMessage
        smsMessage = ''
        data_received_from_Arduino = bus.read_i2c_block_data(addr, 0,29)
        #print (data_received_from_Arduino)
        for i in range(len(data_received_from_Arduino)):
            smsMessage = smsMessage + chr(data_received_from_Arduino[i])

        #print(smsMessage.encode('utf-8'))
        print(smsMessage)
        data_received_from_Arduino =""
        smsMessage = ""
            
    except:
        print(' Oops! Error')
    
    # Decreasing delay may create more transmission errors.
    #time.sleep(0.0005)
    time.sleep(1)