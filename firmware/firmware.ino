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
unsigned long buttonPressedAt = 0;
const unsigned long modifierHoldTime = 5000;
bool modifierSent = false;
bool modifierActive = false;
int actualButtonState = HIGH;

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

  // --- 2. GESTIONE PULSANTE (CLICK E MODIFICATORE) ---
  int reading = digitalRead(PIN_BUTTON);

  // Se lo stato del pulsante è cambiato (considerando il debounce)
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != actualButtonState) {
      actualButtonState = reading;
      if (actualButtonState == LOW) {
        buttonPressedAt = millis();
        modifierSent = false;
      } else if (!modifierSent) {
        Serial.println("ENC_CLICK");
      }
    }
  }

  if (actualButtonState == LOW && !modifierSent &&
      millis() - buttonPressedAt >= modifierHoldTime) {
    modifierActive = !modifierActive;
    Serial.println(modifierActive ? "ENC_MODIFIER_ON" : "ENC_MODIFIER_OFF");
    modifierSent = true;
  }

  lastButtonState = reading;
}