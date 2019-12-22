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
import json

addr = 0x8 # bus address
bus = SMBus(1) # indicates /dev/ic2-1
#bus.write_byte(addr, 0x1) # switch it on

I2C_buffer_size = 30    #actual size is 32, but the 1st byte is used as a command in this code and last is null termination

# commands I made up to send to arduino (matches commands in ino file)
commandI2CData = 11  #this string contains data
commandI2CDataValidate = 111  #retrieve the incomming buffer; check that the buffer contains expected string
commandLoRaSend = 99  #mark the string complete, which initiates the send
commandGetRSSI = 50  #request the current RSSI value
commandSetTimeout = 51   #set a new value for HeartBeatDelayMax
commandGetFrequencyError = 52   #request the last measured frequency error. 
commandGetLastSNR = 53          #request the Signal-to-noise ratio (SNR) of the last received message
commandGetLoRaStatus = 1    #request is radio ready
commandGetInLockStatus = 2    #request is in-buffer available
commandGetOutLockStatus = 3     #request is out-buffer available
commandGetLoRaDataReady = 4       #request is out-buffer completed
commandSetTargetNode = 9            #update the current target (where to send LoRa messages)
commandSetPower = 10                  #update power setting for the radio 5 to 23
commandReset = 0            #reboots the Arduino and the radio

sample_dataBIG = {
    "Environment": {
        "Temperature": 71.05,
        "Humidity": 23.4,
        "Pressure": 19.032
    },
    "RPi Conditions": {
        "CPU": 45.2,
        "Mem": 86.9,
        "Temperature": 72.8
    },
    "Alerts": {
        "Info": "sample message"
    }
}

sample_data = {
    "Environment": {
        "Temperature": 71.05,
        "Humidity": 23.4,
        "Pressure": 19.032
    }
}

sample_json = json.dumps(sample_data)

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

print("sending")
waitForRadio()      #hang here until the radio buffers are clear
writeData("aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ1234567890")   
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandLoRaSend,15)
print (arrayToString(data_received_from_Arduino))

#***** get status of the recieving buffer. if this is true, there is no place to store uploading data
#data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetLoRaDataReady,5)
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandGetLoRaDataReady,5))
print("LoRaDataReady status:", smsMessage)

waitForRadio()      #hang here until the radio buffers are clear
writeData("simple")   
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandLoRaSend,15)
print (arrayToString(data_received_from_Arduino))

waitForRadio()      #hang here until the radio buffers are clear
writeData(sample_json)   
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandLoRaSend,15)
print (arrayToString(data_received_from_Arduino))


#***** get RSSI
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandGetRSSI,5))
print("RSSI:", smsMessage)

#***** get frequency Error
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandGetFrequencyError,5))
print("Frequency Error (Hz):", smsMessage)

#***** get Signal Noise Ratio
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandGetLastSNR,5))
print("Signal to Noise Ratio:", smsMessage)

#***** set Heartbeat timeout
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandSetTimeout,StringToBytes("6000"))
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandSetTimeout,5))
print("Heartbeat Timeout:", smsMessage)
smsMessage = ""

#***** get status outgoing lock (1= locked)
smsMessage = ''
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetOutLockStatus,5)
#print (data_received_from_Arduino)
for i in range(len(data_received_from_Arduino)):
    if (data_received_from_Arduino[i] == 0):
        #end of string found
        break
    else:
        smsMessage = smsMessage + chr(data_received_from_Arduino[i])
print("Out Lock status:", smsMessage)
data_received_from_Arduino =""
smsMessage = ""

#***** get status outgoing lock (1= locked)
smsMessage = ''
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetInLockStatus,5)
#print (data_received_from_Arduino)
for i in range(len(data_received_from_Arduino)):
    if (data_received_from_Arduino[i] == 0):
        #end of string found
        break
    else:
        smsMessage = smsMessage + chr(data_received_from_Arduino[i])
print("In Lock status:", smsMessage)
data_received_from_Arduino =""
smsMessage = ""

#***** get buffer
# note: I wrote the Arduino side to step through the buffer with consecutive "commandI2CDataValidate" calls
#       If another request happens in the middle, the send restarts at the buffer's begining
smsMessage = ''
endOfString = False     #has null-terminator been found
loopMax = 250//I2C_buffer_size+1    #prevent infinate loop don't bother looking for more data then would fit in the buffer
loopCount = 0
while (not endOfString and loopCount < loopMax):
    loopCount +=1
    data_received_from_Arduino = bus.read_i2c_block_data(addr, commandI2CDataValidate,32)
    #print (data_received_from_Arduino)
    for i in range(len(data_received_from_Arduino)):
        if (data_received_from_Arduino[i] == 0x00):
            #end of string found
            endOfString = True
            break
        else:
            smsMessage = smsMessage + chr(data_received_from_Arduino[i])
    #time.sleep(.1)
#print(smsMessage.encode('utf-8'))
print("Send buffer: ", smsMessage)
data_received_from_Arduino =""
smsMessage = ""

#***** set a new address to send LoRa messages to
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandSetTargetNode,StringToBytes("2"))
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandSetTargetNode,5))
print("Target Node:", smsMessage)
smsMessage = ""

#***** try to send to absent target
waitForRadio()      #hang here until the radio buffers are clear
writeData("NewTarget")   
data_received_from_Arduino = bus.read_i2c_block_data(addr, commandLoRaSend,15)
print (arrayToString(data_received_from_Arduino))

#***** set a new power level 5 to 23
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandSetPower,StringToBytes("5"))
smsMessage = arrayToString(bus.read_i2c_block_data(addr, commandSetPower,5))
print("Power Level:", smsMessage)
smsMessage = ""



#***** REBOOT the radio and Arduino
print("Waiting to reboot the Arduino")
time.sleep(5000)
smsMessage = ''
data_received_from_Arduino = bus.write_i2c_block_data(addr,commandReset,StringToBytes(""))
print("Arduino rebooting. Hope it recovers")
smsMessage = ""


# while 1:
    # try:
        # # data = bus.read_byte(addr)
        # # print('data {}'.format(data))
        # #global smsMessage
        # smsMessage = ''
        # data_received_from_Arduino = bus.read_i2c_block_data(addr, commandGetRSSI,29)
        # #print (data_received_from_Arduino)
        # for i in range(len(data_received_from_Arduino)):
            # smsMessage = smsMessage + chr(data_received_from_Arduino[i])

        # #print(smsMessage.encode('utf-8'))
        # print("Received from I2C: ", smsMessage)
        # data_received_from_Arduino =""
        # smsMessage = ""
            
    # except:
        # print(' Oops! Error')
    
    # # Decreasing delay may create more transmission errors.
    # #time.sleep(0.0005)
    # time.sleep(1)