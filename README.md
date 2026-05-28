# Root-Game-Engine

### Training a fast Woodland Alliance policy

`main.py` can train a quick imitation policy for the Woodland Alliance. It rolls
out games against the built-in Marquise and Eyrie AIs, labels each Alliance
position with a cheap heuristic expert, and trains `AllianceNN` to copy those
choices. The saved model then acts with one neural-network forward pass plus the
legal-action mask.

Quick smoke run:

```bash
python main.py train --games 5 --max-alliance-decisions 40 --epochs 2 --checkpoint alliance_policy.pt
```

Stronger local run:

```bash
python main.py train --games 100 --max-alliance-decisions 150 --epochs 12 --batch-size 128 --checkpoint alliance_policy.pt
```

Evaluate or render a saved policy:

```bash
python main.py run --checkpoint alliance_policy.pt --games 10 --render-output game_state.png
```

### TODO:
1. Add crafting items and limits
2. Add vagabound functionality

### FIX NOW:
1. 
