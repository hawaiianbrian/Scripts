#!/usr/bin/env python3
"""
d20_decision.py — Cybersecurity Decision D20 Roller (CLI)

Interactive version:
- Prompts for whether input is from analyst or senior leadership.
- Senior leadership gets +3 bonus.
- Natural 1 => Never Taking Your Advice, Again!
- 2–10 => failure
- 11–19 => success
- Natural 20 or total >= 20 => Natty 20, Lets GO!!!
"""

import random
import json
from datetime import datetime, timezone


def dice_roller(sides: int = 20) -> int:
    """Roll a dice with the given number of sides (default D20)."""
    return random.randint(1, sides)


def evaluate_decision(base_roll: int, source: str, modifier: int) -> dict:
    """Evaluate decision outcome based on D20 roll and source modifier."""
    # +3 input from Senior Leadership
    if source.lower().strip() in {"senior leadership", "senior", "exec", "executive"}:
        modifier += 3

    total = base_roll + modifier

    # Determine result
    if base_roll == 1:
        category = "never"
        message = "Never Taking Your Advice, Again!"
    elif base_roll == 20 or total >= 20:
        category = "brilliant"
        message = "Natty 20, Lets GO!!!"
    elif total <= 10:
        category = "failure"
        message = "Let's try a different idea."
    else:
        category = "success"
        message = "Let's roll with it."

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "base_roll": base_roll,
        "modifier": modifier,
        "total": total,
        "category": category,
        "message": message,
    }


def main():
    print("\n=== Cybersecurity Decision D20 Roller ===")
    print("This tool helps you decide if a security idea should proceed.")
    print("-------------------------------------------------------------")

    # Ask who the idea came from
    source = input("Who proposed this idea? (analyst/senior leadership): ").strip() or "analyst"

    # Ask for any extra modifier
    try:
        modifier = int(input("Enter additional modifier (press Enter for 0): ") or 0)
    except ValueError:
        modifier = 0

    # Roll
    roll = dice_roller(20)
    result = evaluate_decision(roll, source, modifier)

    # Display result
    print("\n🎲 D20 Roll Results")
    print("--------------------")
    print(f"Base Roll: {result['base_roll']}")
    print(f"Source: {result['source']}")
    print(f"Modifier: {result['modifier']:+d}")
    print(f"Total: {result['total']}")
    print(f"Outcome: {result['category'].upper()} — {result['message']}")
    print(f"Timestamp: {result['timestamp']}\n")

    # Option to save to JSON
    save = input("Save result to JSON file? (y/n): ").strip().lower()
    if save == "y":
        filename = f"d20_result_{result['timestamp'].replace(':','-')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"✅ Result saved to {filename}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
