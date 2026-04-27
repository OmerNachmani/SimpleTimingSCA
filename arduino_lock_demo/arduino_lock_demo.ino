/*
 * arduino_lock_demo.ino
 *
 * Educational demo of a 4-digit PIN lock that is intentionally vulnerable
 * to a timing side-channel attack. The check loop bails out (and adds a
 * per-character delay) on the first wrong digit, so a correct prefix takes
 * measurably longer to verify than a wrong one. The companion script
 * timing_attack_first_demo.py exploits this to recover the PIN one digit
 * at a time.
 *
 * Hardware:
 *   - Arduino Uno / Nano / compatible
 *   - 4x4 matrix keypad on digital pins 2..9
 *   - Green status LED on D10, red status LED on D11 (with current-limit Rs)
 *
 * The sketch also accepts PIN attempts over the USB serial line, which is
 * how the Python attacker drives it.
 *
 * NOTE: This is a teaching artifact. Do not use this code (or anything
 * resembling it) for a real lock.
 */

#include <Keypad.h>

// ---------- Keypad wiring ----------
const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[ROWS] = {2, 3, 4, 5};
byte colPins[COLS] = {6, 7, 8, 9};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// ---------- System configuration ----------
const String SECRET_PIN = "8975";   // The "secret" PIN to recover
const int   GREEN_LED   = 10;
const int   RED_LED     = 11;
const int   PIN_LENGTH  = 4;
const int   PER_DIGIT_DELAY_MS = 5; // Amplifies the timing leak so it is
                                    // visible over the USB serial round trip.

String inputBuffer = "";

void setup() {
  Serial.begin(9600);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  Serial.println("--- System Online ---");
  Serial.println("Enter PIN on Keypad or via Serial:");
}

void loop() {
  // 1. Read from the physical keypad
  char key = keypad.getKey();
  if (key) {
    Serial.print("*"); // Echo a masked character
    inputBuffer += key;
    if (inputBuffer.length() == PIN_LENGTH) {
      checkPin(inputBuffer);
      inputBuffer = "";
    }
  }

  // 2. Read from the serial port (used by the attacker script)
  if (Serial.available() > 0) {
    String serialInput = Serial.readStringUntil('\n');
    serialInput.trim();
    if (serialInput.length() == PIN_LENGTH) {
      checkPin(serialInput);
    }
  }
}

/*
 * Vulnerable PIN check.
 *
 * The loop early-exits on the first mismatching character and inserts a
 * fixed delay between successful character comparisons. The total time
 * therefore scales with the length of the correct prefix, which is the
 * leak the attacker measures.
 *
 * A constant-time comparison would compare all characters unconditionally
 * and combine the results with bitwise OR before branching once at the end.
 */
void checkPin(String attempt) {
  bool isMatch = true;

  for (int i = 0; i < PIN_LENGTH; i++) {
    if (attempt[i] != SECRET_PIN[i]) {
      isMatch = false;
      break;
    }
    delay(PER_DIGIT_DELAY_MS);
  }

  if (isMatch) {
    Serial.println("RESULT:SUCCESS");
    digitalWrite(GREEN_LED, HIGH);
    delay(2000);
    digitalWrite(GREEN_LED, LOW);
  } else {
    Serial.println("RESULT:FAIL");
    digitalWrite(RED_LED, HIGH);
    delay(400);
    digitalWrite(RED_LED, LOW);
  }
}
