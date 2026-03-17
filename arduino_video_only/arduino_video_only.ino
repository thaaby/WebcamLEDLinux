#include <FastLED.h>

#define NUM_LEDS 1024
#define DATA_PIN 6
#define BRIGHTNESS 40

CRGB leds[NUM_LEDS];

void setup() {
  Serial.begin(500000);
  Serial.setTimeout(100);
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  
  // LED built-in per debug
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  // Pulisci subito i LED all'accensione
  FastLED.clear();
  FastLED.show();
}

void loop() {
  // Aspetta il magico byte 'V'
  if (Serial.available() > 0) {
    if (Serial.read() == 'V') {
      
      // Legge esattamente 3072 byte
      int bytesRead = Serial.readBytes((char*)leds, NUM_LEDS * 3);
      
      if (bytesRead == NUM_LEDS * 3) {
        // Accende il LED 13 per indicare ricezione ok
        digitalWrite(13, HIGH);
        
        // MOSTRA I LED! 
        FastLED.show();
        
        // MANDA L'ACK AL PYTHON
        Serial.write('K');
        
        // Spegne il LED 13
        digitalWrite(13, LOW);
      } else {
        // Timeout o frammento perso. Svuota il buffer per rimettersi in sincro
        while(Serial.available() > 0) Serial.read();
      }
    }
  }
}
