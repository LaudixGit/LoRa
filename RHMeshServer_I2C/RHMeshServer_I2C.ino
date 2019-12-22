// https://www.airspayce.com/mikem/arduino/RadioHead/rf22_mesh_server1_8pde-example.html
// rf22_mesh_server1.pde
// -*- mode: C++ -*-
// Example sketch showing how to create a simple addressed, routed reliable messaging server
// with the RHMesh class.
// It is designed to work with the other examples rf22_mesh_*
// Hint: you can simulate other network topologies by setting the 
// RH_TEST_NETWORK define in RHRouter.h
// Mesh has much greater memory requirements, and you may need to limit the
// max message length to prevent wierd crashes

// original converted to work with RF95
// https://raw.githubusercontent.com/rpsreal/LoRa_Ra-02_Arduino/master/LORA_CLIENT.ino

//add I2C - enough RAM?

#include <Wire.h>
#include <RHMesh.h>
//#include <RH_RF22.h>
#include <RH_RF95.h>
#include <SPI.h>
#include <EEPROM.h>  //set the Arduino address by using Mesh_SetNodeID.ino

// In this small artifical network of 4 nodes,
#define RH_MESH_MAX_MESSAGE_LEN 50
#define CLIENT_ADDRESS 1
#define SERVER1_ADDRESS 4
#define SERVER2_ADDRESS 3
#define SERVER3_ADDRESS 2

#define RFM95_CS 10
#define RFM95_RST 9
#define RFM95_INT 2

// Change to 434.0 or other frequency, must match RX's freq!
#define RF95_FREQ 434.0

// What I2C address should be used
#define I2C_ADDRESS 0x8
#define I2C_Buffer_Size 32    //size can exceed 32, but I don't use it that way

//in/out registers
// do NOT use Strings - causes memory issues in Arduino
// https://forum.arduino.cc/index.php?topic=589640.0
// http://www.cplusplus.com/reference/cstring/
volatile char I2Cincoming[I2C_Buffer_Size];             // partial string received from I2C
volatile char LoRaDataToSend[RH_MESH_MAX_MESSAGE_LEN];    // entire string received from I2C
volatile char I2Coutgoing[I2C_Buffer_Size];    //ready to send to I2C
uint8_t LoRaDataReceived[RH_MESH_MAX_MESSAGE_LEN];  //results from the radio

// Define global variables
int8_t send_ack=0;   // flag var
volatile boolean LoRaReady = false;       // is the other radio responding
volatile boolean LoRaDataReady = false;   // is the DATA ready to be sent
volatile boolean LoRaDataInLock = false;    // used to prevent overwriting the I2C in-buffer while it is being sent thru the radio
volatile boolean LoRaDataOutLock = false;    // used to prevent overwriting the I2C out-buffer while it is being sent thru the radio
#define HeartBeatDelayMax  5000           //how many timer 'cycles' to wait until retrying SYN
volatile int HeartBeatDelayCount = 0;     //holds the number of cycles that have passed (see ISR below)
volatile int currentCommand = 0;          //holds the last command received
volatile int I2CNextChar = 0;             //holds the position into the buffer that will be sent next request
#define commandI2CData  11                //incomming buffer holds data
#define commandI2CDataValidate  111       //return the incomming buffer
#define commandLoRaSend 99                //mark the string complete, which initiates the send
#define commandGetRSSI  50                //request the current RSSI value

#define asciiSYN 22   //used in LoRa handshaking
#define asciiACK 6    //used in LoRa handshaking
#define asciiNAK 21   //used in LoRa handshaking; THIS radio is not ready to receive data
#define asciiEOT 4    //used in LoRa handshaking
#define asciiENQ 5    //used in LoRa handshaking; remote radio asking if there is any data waiting HERE
#define asciiSTX 2    //used in LoRa handshaking; remainder of buffer contains data
#define asciiCAN 24   //used in LoRa handshaking; invalid command (1st byte) received; don't know what to do with it
#define asciiNUL 0    //indicate empty buffer -end of string; nothing to do here (ignore)

// Singleton instance of the radio driver
// RH_RF22 driver;
RH_RF95 driver(RFM95_CS, RFM95_INT);

// Class to manage message delivery and receipt, using the driver declared above
RHMesh manager(driver, EEPROM.read(0));

//##################################################################################
void setup() 
{
  // initialize timer2  (note Time1 is used by Wire.h)
  // max out the match register and the prescaler
  // interrupt frequency (Hz) = (Arduino clock speed 16,000,000Hz) / (prescaler * (compare match register + 1))
  // = 977Hz (fires 977 times per second ~ every ms)
  // might have to TURN OFF to avoid any conflict with the Radio ISR
  noInterrupts();           // disable all interrupts
  TCCR2A = 0;               // set entire TCCR2A register to 0
  TCCR2B = 0;               // same for TCCR2B
  TCNT2  = 0;               // initialize counter value to 0
  OCR2A = 255;              // Max match register = 255
  TCCR2A |= (1 << WGM21);   // turn on CTC mode
  TCCR2B |= (1 << CS22);    // Set CS22 bit for 64 prescaler
  TIMSK2 |= (1 << OCIE2A);  // enable timer compare interrupt
  interrupts();             // enable all interrupts
  // done configuring interupts

  // initiate the I2C
  Wire.begin(I2C_ADDRESS);      // join i2c bus with address #0x8
  Wire.onReceive(receiveI2C);   // register event
//  Wire.onRequest(sendI2C);      // sendData is funtion called when Pi requests data

  // manual LoRa reset
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);
  delay(100);
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  Serial.begin(115200);
  if (!manager.init())
    Serial.println("init failed");
  // Defaults after init are 434.0MHz, 0.05MHz AFC pull-in, modulation FSK_Rb2_4Fd36

  // The default transmitter power is 13dBm, using PA_BOOST.
  // If you are using RFM95/96/97/98 modules which uses the PA_BOOST transmitter pin, then 
  // you can set transmitter powers from 5 to 23 dBm:
  driver.setTxPower(23);
  
    Serial.print("addr: "); Serial.println(manager.thisAddress());
}

//##################################################################################
void loop()
{
  uint8_t len = sizeof(LoRaDataReceived);
  uint8_t msgFrom;    
  uint8_t msgTo;    
  uint8_t msgID;    
  uint8_t msgFlags;    
  //LoRaDataInLock = true;    // let other routines know the buffer is in-use
  //LoRaDataReceived[0] = 0;    // set buffer to zero-length; essentially empty the buffer
  if (manager.recvfromAckTimeout(LoRaDataReceived, &len, 3000, &msgFrom, &msgTo, &msgID, &msgFlags))
  {
//    Serial.print("from : 0x");
//    Serial.print(from, HEX);
//    Serial.print(": ");
//    Serial.println((char*)LoRaDataReceived);
    Serial.print("from: 0x");
    Serial.print(msgFrom, HEX);
    Serial.print(" (");
    Serial.print(driver.lastRssi(), DEC);
    Serial.print(",");
    Serial.print(msgTo);
    Serial.print(",");
    Serial.print(msgID);
    Serial.print(",");
    Serial.print(msgFlags, BIN);
    Serial.print("): ");
    Serial.println((char*)LoRaDataReceived);

    // Send a reply back to the originator client
    strncpy(LoRaDataToSend, LoRaDataReceived, len);
    if (manager.sendtoWait(LoRaDataToSend, sizeof(LoRaDataToSend), msgFrom) != RH_ROUTER_ERROR_NONE)
      Serial.println("failed");
  }
}

//##################################################################################
// when Timer2 hits 3 sec (set above) 
// set the flag so that next rune another SYN/ACK occurs
// Timer TURNED OFF to avoid any conflict with the Radio ISR
ISR(TIMER2_COMPA_vect){
  if (HeartBeatDelayCount < HeartBeatDelayMax){
    //haven't waited long enough. increase count, and keep waiting
    HeartBeatDelayCount++;
  }
  else{
    // waited long enough. set flag to retry SYN and reset counter
    LoRaReady = false;
    HeartBeatDelayCount = 0;
  }
}

//##################################################################################
// function that executes whenever data is received from master
// this function is registered as an event, see setup()
// Remove all Serial.print from production code (to avoid events within events)
// https://arduino.stackexchange.com/questions/47947/sending-a-string-from-rpi-to-arduino-working-code
// https://github.com/porrey/i2c/blob/master/Arduino/i2c_Slave/i2c_Slave.ino
// void receiveEvent(uint8_t byteCount)
void receiveI2C(int howMany) {
  int priorCommand = currentCommand;  //temorarily hold on the older command (to check for repeat calls)
  while (Wire.available()) { // loop through all in buffer
      currentCommand = Wire.read();  //the 1st byte is always a command
      //Serial.print("currentCommand received: "); Serial.println(currentCommand);
      for (int i = 0; i < howMany-1; i++) {
        I2Cincoming[i] = Wire.read();
        //Serial.print("I2Cincoming received: "); Serial.println(I2Cincoming[i]);
        I2Cincoming[i + 1] = '\0'; //add null after ea. char
      }
  
    switch (currentCommand)
    {
      case commandI2CData:
        // aggregate the incoming parts into a single string
        //Serial.println((char*)I2Cincoming);
        if (strlen(LoRaDataToSend)==0) {
          // the string is empty
          // set the 1st char (aka the 'command') to indicate the buffer contains data
          LoRaDataToSend[0] = asciiSTX;
          LoRaDataToSend[1] = asciiNUL;  //ensure end of string
        }
        strncat ( LoRaDataToSend, I2Cincoming, sizeof(LoRaDataToSend) );
        break;
      case commandLoRaSend:
        // done assembling the data string. start the send process
        LoRaDataReady = true;
        //Serial.println("Command LoRaSend");
        break;
      case commandI2CDataValidate:
        //if this is a new request, reset pointer, otherwise leave alone
        if (priorCommand == currentCommand){
          //no action at this time
        }
        else{
          //was doing something else before, now a new request, so start at the beginning
          I2CNextChar = 0;
        }
    }
  }
}
