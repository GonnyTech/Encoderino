#include <Encoder.h>

// Definiamo i pin per l'encoder (usiamo i pin 2 e 3 che supportano gli interrupt su Arduino Uno)
const int PIN_ENCODER_CLK = 2;
const int PIN_ENCODER_DT = 3;
const int PIN_BUTTON = 4;

// Inizializza la libreria Encoder
Encoder myEnc(PIN_ENCODER_CLK, PIN_ENCODER_DT);

long oldPosition = -999;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50; // Antirimbalzo per il pulsante

void setup() {
  Serial.begin(9600);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  
  // Messaggio di avvio pulito
  Serial.println("STATUS:READY");
}

void loop() {
  // --- 1. GESTIONE ROTAZIONE ---
  long newPosition = myEnc.read();
  
  // L'encoder a impulsi standard fa 4 scatti per singolo "click" fisico udibile.
  // Dividiamo per 4 per avere un movimento a scatti pulito e coerente.
  long scaledPosition = newPosition / 4;
  long oldScaledPosition = oldPosition / 4;

  if (scaledPosition != oldScaledPosition) {
    if (scaledPosition > oldScaledPosition) {
      Serial.println("ENC_RIGHT");
    } else {
      Serial.println("ENC_LEFT");
    }
    oldPosition = newPosition;
  }

  // --- 2. GESTIONE PULSANTE (CLICK) ---
  int reading = digitalRead(PIN_BUTTON);

  // Se lo stato del pulsante è cambiato (considerando il debounce)
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    // Se il pulsante è premuto (LOW a causa del PULLUP)
    static int actualState = HIGH;
    if (reading != actualState) {
      actualState = reading;
      if (actualState == LOW) {
        Serial.println("ENC_CLICK");
      }
    }
  }
  lastButtonState = reading;
}