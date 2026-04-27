# SimpleTimingSCA

A minimal, hands-on demonstration of a **timing side-channel attack** against
a 4-digit PIN lock running on an Arduino. Built for teaching: small enough to
read in one sitting, big enough to actually crack a "secret" PIN over USB
serial in a few seconds.

## How it works

The Arduino sketch implements a deliberately vulnerable PIN check:

```cpp
for (int i = 0; i < PIN_LENGTH; i++) {
    if (attempt[i] != SECRET_PIN[i]) {
        isMatch = false;
        break;          // <-- early exit on first mismatch
    }
    delay(PER_DIGIT_DELAY_MS);   // <-- amplifies the leak
}
```

Because the loop bails out on the first wrong character, a guess that shares
a longer correct prefix with the secret takes measurably longer to reject.
The Python attacker measures the round-trip time of each guess and recovers
the PIN one digit at a time:

1. Try every candidate digit in position *N* (with the already-recovered
   prefix held fixed).
2. The candidate that produced the longest response time is the correct
   digit for position *N*.
3. Repeat for position *N+1*.

A constant-time comparison (compare every byte unconditionally and combine
the results with bitwise OR) closes this leak.

## Repository layout

```
arduino_lock_demo/
    arduino_lock_demo.ino    # vulnerable PIN lock, runs on the Arduino
timing_attack_first_demo.py  # attacker script, runs on the host PC
```

## Hardware

- Arduino Uno / Nano / any ATmega328P-class board
- 4x4 matrix keypad on digital pins **D2..D9**
- Green LED on **D10**, red LED on **D11** (each in series with ~330 Ω)
- USB cable to the host PC

## Setup

### Arduino side

1. Install the [Keypad](https://www.arduino.cc/reference/en/libraries/keypad/)
   library via the Arduino Library Manager.
2. Open `arduino_lock_demo/arduino_lock_demo.ino` in the Arduino IDE.
3. Optionally change `SECRET_PIN` to something else (4 characters from the
   keypad alphabet `0-9 A-D * #`).
4. Upload to the board and note which serial port it enumerates as
   (`/dev/ttyACM0`, `/dev/ttyUSB0`, `COM3`, ...).

### Host side

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install pyserial
```

## Running the attack

```bash
python timing_attack_first_demo.py --port /dev/ttyACM0
```

The script prints a per-position table of measured round-trip times. The
slowest row in each table is the recovered digit; after four rounds it
prints the full PIN and offers to send it back to the Arduino to unlock.

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE).
