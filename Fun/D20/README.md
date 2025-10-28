# d20_decision — Cybersecurity Decision D20 (CLI)

Roll a D20 to “decide” security ideas, with a **+3** buff for senior leadership.

## Rules
- **Natural 1**  → Don't Ever Make Suggestions  
- **2–10**       → Failure (reject)  
- **11–19**      → Success (proceed with caution)  
- **Natural 20** or **total ≥ 20** → Natty 20, Lets GO!!! 
- **Senior leadership** adds **+3**

## Quick Start
```bash
chmod +x d20_decision.py

# Basic roll
./d20_decision.py

# Senior leadership (+3)
./d20_decision.py --senior

# Multiple rolls
./d20_decision.py -n 5

# JSON output (great for logs/automation)
./d20_decision.py --json --senior -n 2

# Seed for reproducibility
./d20_decision.py --seed 42 -n 3

# Exit code (0 = proceed, 1 = reject) - useful in CI gates
./d20_decision.py --exit-code --senior
