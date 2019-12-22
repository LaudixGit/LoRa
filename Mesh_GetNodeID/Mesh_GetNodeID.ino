// https://raw.githubusercontent.com/nootropicdesign/lora-mesh/master/SetNodeId/SetNodeId.ino

// read the node's ID in EEPROM (see Mesh_SetNodeID)

#include <EEPROM.h>

uint8_t nodeId;

void setup() {
  Serial.begin(115200);
  while (!Serial) ; // Wait for serial port to be available

  nodeId = EEPROM.read(0);
  Serial.print(F("nodeId = "));
  Serial.println(nodeId);

}

void loop() {

}
