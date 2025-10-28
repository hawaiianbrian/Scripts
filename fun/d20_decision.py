#!/usr/bin/env python3
"""
d20_decision.py — Cybersecurity Decision D20 Roller (CLI)

Rules:
- Natural 1  => "What an Awful Suggestion."
- 2–10       => failure
- 11–19      => success
- Natural 20 or total >= 20 => "Natty 20, LETS GO!!!"
- +3 bonus for ideas from senior leadership

Notes:
- Natural 1 and 20 override modifiers.
- Supports multiple rolls, seeding, JSON output, and exit codes for automation.
"""

import argparse
import json
import random
from datetime import datetime, timezone


def dice_roller(sides: int = 20) -> int:
    """Roll a dice with the given number of sides (default D20)."""
    return random.randint(1, sides)


def evaluate_decision(base_roll: int, source: str, modifier: int) -> dict:
    """Evaluate decision outcome based on D20 roll and source modifier."""
    # +3 for senior leadership input
    if source.lower().strip() in {"senior leadership", "senior", "exec", "executive"}:
        modifier += 3

    total = base_roll + modifier

    # Natural 1 = auto fail
    if base_roll == 1:
        category = "never"
        message = "NEVER take that advice."
    # Natural 20 or total >= 20 = automatic brilliant
    elif base_roll == 20 or total >= 20:
        category = "brilliant"
        message = "Brilliant idea — full steam ahead!"
    # Total ≤ 10 = failure
    elif total <= 10:
        category = "failure"
        message = "Decision failed — reject the idea."
    # Total 11–19 = success
    else:
        category = "success"
        message = "Decision successful — proceed with caution."

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
    parser = argparse.ArgumentParser(
        description="Roll a D20 to make cybersecurity decisions (with optional +3 for Senior Leadership)."
    )
    parser.add_argument("-s", "--source", default="general",
                        help='Who proposed it (e.g., "senior leadership", "analyst").')
    parser.add_argument("-m", "--modifier", type=int, default=0,
                        help="Additional modifier to apply (default: 0).")
    parser.add_argument("--senior", action="store_true",
                        help="Shorthand to apply +3 (equivalent to --source 'senior leadership').")
    parser.add_argument("-n", "--rolls", type=int, default=1,
                        help="Number of rolls to perform (default: 1).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed RNG for reproducible results.")
    parser.add_argument("--json", action="store_true",
                        help="Output results in JSON format (array if multiple rolls).")
    parser.add_argument("--exit-code", action="store_true",
                        help="Exit 0 on success/brilliant, 1 on failure/never (based on last roll).")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    source = "senior leadership" if args.senior else args.source

    results = []
    for _ in range(max(1, args.rolls)):
        roll = dice_roller(20)
        results.append(evaluate_decision(roll, source, args.modifier))

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            print(f"🎲 D20: {r['base_roll']}  (modifier {r['modifier']:+d})  => total {r['total']}")
            print(f"   Source: {r['source']}")
            print(f"   Result: {r['category'].upper()} — {r['message']}\n")

    if args.exit_code:
        last = results[-1]["category"]
        raise SystemExit(0 if last in {"success", "brilliant"} else 1)


if __name__ == "__main__":
    main()
