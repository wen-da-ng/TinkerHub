#include <Arduino.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <AsyncWebSocket.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <esp_now.h>

const char* ssid = "ESP32-AP";
const char* password = "password123";
const int CHANNEL = 1;

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

struct SensorData {
  float values[18];
};

struct ControlData {
  String action;
};

SensorData sensorData;
ControlData controlData;

uint8_t secondUnitAddress[] = {0xD4, 0xF9, 0x8D, 0x05, 0x83, 0x70};

void OnDataRecv(const uint8_t * mac_addr, const uint8_t *incomingData, int len) {
  memcpy(&sensorData, incomingData, sizeof(sensorData));
  
  DynamicJsonDocument doc(1024);
  for (int i = 0; i < 18; i++) {
    doc[String("data") + String(i)] = sensorData.values[i];
  }
  
  String json;
  serializeJson(doc, json);
  
  ws.textAll(json);
}

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.printf("Last Packet Send Status: %s\n", status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;
  if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
    data[len] = 0;
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, (char*)data);
    
    if (doc.containsKey("action")) {
      controlData.action = doc["action"].as<String>();
      esp_err_t result = esp_now_send(secondUnitAddress, (uint8_t *)&controlData, sizeof(controlData));
      if (result != ESP_OK) {
        Serial.println("Error sending the control data");
      }
      Serial.println("Action received: " + controlData.action);
    }
  }
}

void onEvent(AsyncWebSocket *server, AsyncWebSocketClient *client, AwsEventType type,
             void *arg, uint8_t *data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
      break;
    case WS_EVT_DISCONNECT:
      Serial.printf("WebSocket client #%u disconnected\n", client->id());
      break;
    case WS_EVT_DATA:
      handleWebSocketMessage(arg, data, len);
      break;
    case WS_EVT_PONG:
    case WS_EVT_ERROR:
      break;
  }
}

void setup() {
  Serial.begin(115200);
  
  if(!LittleFS.begin()){
     Serial.println("An Error has occurred while mounting LittleFS");
     return;
  }

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(ssid, password, CHANNEL);
  Serial.println("Access Point Started");
  Serial.print("AP IP Address: ");
  Serial.println(WiFi.softAPIP());

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);
  esp_now_register_recv_cb(OnDataRecv);

  esp_now_peer_info_t peerInfo;
  memcpy(peerInfo.peer_addr, secondUnitAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }

  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");
  
  // Add this line to serve the Tailwind CSS file if you're hosting it locally
  server.on("/tailwind.css", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/tailwind.css", "text/css");
  });
  
  ws.onEvent(onEvent);
  server.addHandler(&ws);

  server.begin();
  Serial.println("HTTP server started");

  Serial.print("AP MAC: ");
  Serial.println(WiFi.softAPmacAddress());
}

void loop() {
  ws.cleanupClients();
  
  // Simulate data if no data is received from the second unit
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate > 1000) {  // Send updates every second
    bool dataReceived = false;
    for (int i = 0; i < 18; i++) {
      if (sensorData.values[i] != 0) {
        dataReceived = true;
        break;
      }
    }
    
    if (!dataReceived) {
      for (int i = 0; i < 18; i++) {
        sensorData.values[i] = random(100);  // Simulated data
      }
      
      DynamicJsonDocument doc(1024);
      for (int i = 0; i < 18; i++) {
        doc[String("data") + String(i)] = sensorData.values[i];
      }
      
      String json;
      serializeJson(doc, json);
      ws.textAll(json);
    }
    
    lastUpdate = millis();
  }
  
  delay(10);
}