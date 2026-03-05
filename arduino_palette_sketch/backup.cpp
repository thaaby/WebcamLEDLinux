#include <FastLED.h>

// --- CONFIGURAZIONE MATRICE ---
#define LED_PIN     6
#define NUM_LEDS    256     // Matrice 8x32
#define BRIGHTNESS  40      // Sicurezza alimentazione
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB
#define MAX_PALETTE 49      // Max colori (7x7 griglia)

CRGB leds[NUM_LEDS];

// --- CALIBRAZIONE COLORE LOEFL1RGB/6024 (CMN Group) ---
const float RED_FACTOR   = 1.00; 
const float GREEN_FACTOR = 0.75; 
const float BLUE_FACTOR  = 0.90;

// === COLORI ===
bool paletteMode = false;
int paletteSize = 0;
int paletteR[MAX_PALETTE];
int paletteG[MAX_PALETTE];
int paletteB[MAX_PALETTE];

int currentR = 0;
int currentG = 0;
int currentB = 0;

// Flag: nuovi dati da mostrare
bool needsUpdate = false;

// Buffer seriale
char inputBuffer[512];  // Grande per 7x7 griglie
int bufferPos = 0;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);
  pinMode(13, OUTPUT);
  
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(BRIGHTNESS);
  FastLED.clear();
  FastLED.show();
}

// Converte 2 caratteri HEX in byte
int hexToByte(char hi, char lo) {
  int val = 0;
  if (hi >= '0' && hi <= '9') val = (hi - '0') << 4;
  else if (hi >= 'A' && hi <= 'F') val = (hi - 'A' + 10) << 4;
  else if (hi >= 'a' && hi <= 'f') val = (hi - 'a' + 10) << 4;
  if (lo >= '0' && lo <= '9') val |= (lo - '0');
  else if (lo >= 'A' && lo <= 'F') val |= (lo - 'A' + 10);
  else if (lo >= 'a' && lo <= 'f') val |= (lo - 'a' + 10);
  return val;
}

// Parse "P:N:RRGGBB:RRGGBB:..." — SOLO parse, NON aggiorna LED
void parsePalette(char* data) {
  char* ptr = data + 2;
  int n = atoi(ptr);
  if (n < 1 || n > MAX_PALETTE) return;
  
  ptr = strchr(ptr, ':');
  if (!ptr) return;
  ptr++;
  
  for (int i = 0; i < n; i++) {
    if (strlen(ptr) < 6) return;
    paletteR[i] = (int)(hexToByte(ptr[0], ptr[1]) * RED_FACTOR);
    paletteG[i] = (int)(hexToByte(ptr[2], ptr[3]) * GREEN_FACTOR);
    paletteB[i] = (int)(hexToByte(ptr[4], ptr[5]) * BLUE_FACTOR);
    ptr += 6;
    if (*ptr == ':') ptr++;
  }
  
  paletteSize = n;
  paletteMode = true;
  needsUpdate = true;  // Segnala che i LED vanno aggiornati
}

// Parse "R,G,B" — SOLO parse, NON aggiorna LED
void parseSingle(char* data) {
  int r = 0, g = 0, b = 0;
  if (sscanf(data, "%d,%d,%d", &r, &g, &b) == 3) {
    currentR = (int)(constrain(r, 0, 255) * RED_FACTOR);
    currentG = (int)(constrain(g, 0, 255) * GREEN_FACTOR);
    currentB = (int)(constrain(b, 0, 255) * BLUE_FACTOR);
    paletteMode = false;
    needsUpdate = true;
  }
}

void loop() {
  // 1. LEGGI TUTTA la seriale (SENZA toccare i LED)
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (bufferPos > 0) {
        inputBuffer[bufferPos] = '\0';
        digitalWrite(13, HIGH);
        
        if (inputBuffer[0] == 'P' && inputBuffer[1] == ':') {
          parsePalette(inputBuffer);
        } else {
          parseSingle(inputBuffer);
        }
      }
      bufferPos = 0;
    } else if (bufferPos < 510) {
      inputBuffer[bufferPos++] = c;
    }
  }
  
  digitalWrite(13, LOW);
  
  // 2. EFFETTO ONDA CONTINUO (eseguito ogni iterazione del loop)
  // Sfuma tutti i LED di una certa quantità (crea la scia)
  fadeToBlackBy(leds, NUM_LEDS, 20); // 20 = velocità di dissolvenza
  
  // Sposta tutti i LED in avanti di un passo (effetto movimento)
  for (int i = NUM_LEDS - 1; i > 0; i--) {
    leds[i] = leds[i - 1];
  }
  
  // 3. SE CI SONO NUOVI DATI, inseriscili all'inizio della striscia (led 0)
  // Per la palette, mescoliamo i colori nel tempo o ne scegliamo uno a rotazione per frame
  if (paletteMode && paletteSize > 0) {
    static int colorIdx = 0;
    // Inserisci il colore corrente della palette al primo LED
    leds[0] = CRGB(paletteR[colorIdx], paletteG[colorIdx], paletteB[colorIdx]);
    
    // Cambia colore alla prossima iterazione (crea un pattern misto se la palette ha più colori)
    colorIdx++;
    if (colorIdx >= paletteSize) {
      colorIdx = 0;
    }
  } else {
    // Singolo colore (quando non c'è griglia o allo spegnimento 0,0,0)
    leds[0] = CRGB(currentR, currentG, currentB);
  }
  
  // 4. Mostra i LED e aspetta un istante per controllare la velocità dell'onda
  FastLED.show();
  delay(20); // Regola questo per la velocità di scorrimento dell'onda
  
  needsUpdate = false; // Flag non più strettamente necessario col loop continuo
}
