#!/usr/bin/env python

# https://create.arduino.cc/projecthub/aardweeno/controlling-an-arduino-from-a-pi3-using-i2c-59817b
# https://arduino.stackexchange.com/questions/47947/sending-a-string-from-rpi-to-arduino-working-code
# https://raspberrypi.stackexchange.com/questions/62206/sending-and-receiving-string-data-between-arduino-and-raspberry-pi-using-the-i2c
# https://buildmedia.readthedocs.org/media/pdf/smbus2/latest/smbus2.pdf
# https://stackoverflow.com/questions/32656722/python-can-i-read-two-bytes-in-one-transaction-with-the-smbus-module
# https://realpython.com/lessons/serializing-json-data/#:~:targetText=The%20json%20module%20exposes%20two,a%20string%20in%20JSON%20format.
# https://realpython.com/python-json/

from smbus import SMBus
import time

addr = 0x8 # bus address
bus = SMBus(1) # indicates /dev/ic2-1

I2C_buffer_size = 30    #actual size is 32, but the 1st byte is used as a command in this code and last is null termination

# commands I made up to send to arduino (matches commands in ino file)
commandI2CData = 11  #this string contains data
commandI2CDataValidate = 111  #retrieve the incomming buffer; check that the buffer contains expected string
commandLoRaSend = 99  #mark the string complete, which initiates the send
commandGetRSSI = 50  #request the current RSSI value
commandSetTimeout = 51   #set a new value for HeartBeatDelayMax
commandGetLoRaStatus = 1    #request is radio ready
commandGetInLockStatus = 2    #request is in-buffer available
commandGetOutLockStatus = 3     #request is out-buffer available
commandGetLoRaDataReady = 4       #request is out-buffer completed
commandSetTargetNode = 9            #update the current target (where to send LoRa messages)
commandSetPower = 10                  #update power setting for the radio 5 to 23
commandReset = 0            #reboots the Arduino and the radio

def writeData(value):
    #how many chunks will it take to read the entire string?
    strValue = str(value)
    chunks = range(len(strValue)//I2C_buffer_size+1)   #add 1 to handle any partial chunks at the end
    for chunk in chunks:
        print("Chunk#: ", chunk)
        chunkStart = chunk * I2C_buffer_size
        valueChunk = strValue[chunkStart:chunkStart+I2C_buffer_size]      #grab the substring begining at this chunk, but only as long as the buffer holds
        #print (valueChunk)
        byteValue = StringToBytes(valueChunk)
        #print ("outgoing string: ", byteValue)
        #bus.write_i2c_block_data(addr,0x00,byteValue)   #first byte is 0=command byte.. just is.
        waitForRadio()      #hang here until the radio buffers are clear
        bus.write_i2c_block_data(addr,commandI2CData,byteValue)   #first byte is the command 
        time.sleep(1)
    return -1

def waitForRadio():
    #if the query returns true, then ther eis no place to load the data; waitForRadio
    # to do: add exit/timeout
    #***** get status of the recieving buffer. if this is true, there is no place to store uploading data
    busy = True
    while busy:
        data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetLoRaDataReady,5)
        #print (data_received_from_Arduino)
        smsMessage = arrayToString(data_received_from_Arduino)
        busy = int(smsMessage)
        if busy: time.sleep(2)       # don't check very often; this call interupts the radio - taking even long to clear the buffer
        #print("Buffer status:", smsMessage)
        data_received_from_Arduino =""
        smsMessage = ""
    
def arrayToString(arIn):
    # convert the c-string from the radio into a string
    strOut = ''
    for i in range(len(arIn)):
        if (arIn[i] == 0):
            #end of string found
            break
        else:
            strOut = strOut + chr(arIn[i])
    return strOut
    
    
def StringToBytes(val):
        retVal = []
        for c in val:
                retVal.append(ord(c))
        return retVal

#***** get status of the radio
#data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetLoRaStatus,5)
#print (data_received_from_Arduino)
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandGetLoRaStatus,5))
print("LoRa status:", smsMessage)
#data_received_from_Arduino =""

#***** set a new address to send LoRa messages to
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandSetTargetNode,StringToBytes("3"))
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandSetTargetNode,5))
print("Target Node:", smsMessage)
smsMessage = ""

#***** try to send to absent target
waitForRadio()      #hang here until the radio buffers are clear
writeData("NewTarget")   
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandLoRaSend,15)
print (arrayToString(data_received_from_Arduino))

