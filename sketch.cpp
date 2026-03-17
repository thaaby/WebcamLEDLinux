#define FASTLED_ALLOW_INTERRUPTS 0
#define FASTLED_INTERRUPT_RETRY_COUNT 0

#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h> 
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <FastLED.h>

const char* ssid = "ledwall2.4";       
const char* password = "meglioinsieme207"; 

// CAMBIA QUI: 51, 52 o 54
IPAddress local_IP(192, 168, 1, 54); 

IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8); 
IPAddress secondaryDNS(8, 8, 4, 4);

#define NUM_LEDS 660
#define DATA_PIN D4
CRGB leds[NUM_LEDS];

WiFiUDP Udp;
const unsigned int localUdpPort = 4210;
byte packetBuffer[1000]; 

bool ota_in_progress = false; 

void setup() {
  Serial.begin(115200);
  WiFi.setSleepMode(WIFI_NONE_SLEEP); 

  // Setup pulito per ledwall artigianale
  FastLED.addLeds<WS2812B, DATA_PIN, RGB>(leds, NUM_LEDS);
  FastLED.setBrightness(100); 

  WiFi.mode(WIFI_STA);
  WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS);
  WiFi.begin(ssid, password);
  
  Serial.print("Connessione a ");
  Serial.print(ssid);
  Serial.print("...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connesso! IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Segnale (RSSI): ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");

  // CAMBIA QUI IL NOME PER OGNI PANNELLO (es. "Ledwall-1", "Ledwall-2")
  ArduinoOTA.setHostname("Ledwall-3"); 
  
  ArduinoOTA.onStart([]() {
    ota_in_progress = true; 
    fill_solid(leds, NUM_LEDS, CRGB::Black); 
    FastLED.show();
  });
  
  ArduinoOTA.onEnd([]() {
    ota_in_progress = false;
  });
  
  ArduinoOTA.begin();
  MDNS.begin("Ledwall-3"); // UGUALE ALL'HOSTNAME

  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
  Udp.begin(localUdpPort);
}

void loop() {
  ArduinoOTA.handle(); 
  MDNS.update();       

  if (ota_in_progress) return;

  int packetSize = Udp.parsePacket();
  
  // Abbassato da 20 a 10 per evitare che l'ESP rimanga incastrato troppo a lungo a leggere
  int maxLetture = 10; 

  while (packetSize > 0 && maxLetture > 0) {
    int len = Udp.read(packetBuffer, 1000);
    
    // Controllo di sicurezza: processa solo se il pacchetto è integro (990 byte dati + 1 etichetta)
    if (len == 991) {
      byte etichetta = packetBuffer[0]; 
      int payloadLen = len - 1;
      
      int ledOffset = (etichetta == 0) ? 0 : 330;
      
      for(int i = 0; i < payloadLen / 3; i++) {
        leds[ledOffset + i] = CRGB(packetBuffer[1 + i*3], packetBuffer[2 + i*3], packetBuffer[3 + i*3]);
      }
    }
    packetSize = Udp.parsePacket();
    maxLetture--;
  }

  EVERY_N_MILLISECONDS(20) {
    FastLED.show();
  }
  
  yield();
}