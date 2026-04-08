import random
import time
from dataclasses import dataclass
from typing import List

#FENCER MODEL
@dataclass
class Fencer:
    name: str
    style: str      #"aggressive", "defensive", "tempo"
    grip: str       #"french", "pistol"
    #skill: float    # base skill level (0-1)

#STYLE LOGIC
STYLE_WEIGHTS = {
    "aggressive": {"attack": 0.6,"parry": 0.2, "feint": 0.2},
    "defensive": {"attack": 0.2, "parry": 0.6, "feint": 0.2},
    "tempo": {"attack":0.3, "parry": 0.2, "feint": 0.5},
}

def choose_action(fencer: Fencer):
    weights = STYLE_WEIGHTS[fencer.style]
    return random.choices(
        ["attack","parry","feint"],
        weights=[weights["attack"],weights["parry"],weights["feint"]]
    )[0]

#INTERACTION MATRIX
INTERACTION_MATRIX = {
    ("attack", "attack"): (0.0, 0.0),
    ("attack", "parry"): (-0.1, +0.1),
    ("attack", "feint"): (+0.1, -0.1),

    ("parry", "attack"): (+0.1, -0.1),
    ("parry", "parry"): (0.0, 0.0),
    ("parry", "feint"): (-0.1, +0.1),

    ("feint", "attack"): (-0.1, +0.1),
    ("feint", "parry"): (+0.1, -0.1),
    ("feint", "feint"): (0.0, 0.0),
}

#GRIP MODIFIER
def grip_modifier(f1: Fencer, f2: Fencer):
    pass

#DOUBLE TOUCH CHANCE
def double_touch_chance(f1: Fencer, f2: Fencer):
    base = 0.05

    #French grips increase double touch chance
    if f1.grip == "french":
        base += 0.05
    if f2.grip == "french":
        base += 0.05

    #Defensive style decreases double touch chance
    if f1.style == "defensive":
        base -= 0.02
    if f2.style == "defensive":
        base -= 0.02

    #tempo style increases double touch chance
    if f1.style == "tempo":
        base += 0.02
    if f2.style == "tempo":
        base += 0.02

    return base

#SINGLE TOUCH RESOLUTION
def resolve_touch(f1: Fencer, f2: Fencer):
    action1 = choose_action(f1)
    action2 = choose_action(f2)

    #Double touch check
    if random.random() < double_touch_chance(f1,f2):
        return 1,1
    
    #base probability
    score1 = 1
    score2 = 1

    #apply interaction matrix
    mod1, mod2 = INTERACTION_MATRIX[(action1, action2)]
    score1 += mod1
    score2 += mod2

    #grip modifiers will go here but empty for now

    #prevent negative probability
    score1 = max(score1, 0.01)
    score2=  max(score2, 0.01)

    total = score1 + score2
    r = random.random()

    if r < score1 / total:
        return 1, 0
    else:
        return 0, 1
    
#BOUT LOGIC
def simulate_bout(f1: Fencer, f2: Fencer, target = 15):
    score1, score2 = 0, 0

    while score1 < target and score2 <target:
        t1,t2 = resolve_touch(f1, f2)
        score1 += t1
        score2 += t2

    return f1 if score1 > score2 else f2

#TOURNAMENT LOGIC
def run_round(fencers: List[Fencer]) -> List[Fencer]:
    winners = []

    for i in range(0, len(fencers),2):
        winner = simulate_bout(fencers[i],fencers[i+1])
        winners.append(winner)

    return winners

def run_tournament(fencers: List[Fencer]) -> Fencer:
    round_num = 1

    while len(fencers) > 1:
        print(f"Round {round_num}: {len(fencers)} fencers")
        fencers = run_round(fencers)
        round_num += 1
    return fencers[0]

#GENERATION HELPER FUNCTIONS
def random_fencer(i):
    return Fencer(
        name=f"Fencer_{i}",
        style=random.choice(["aggressive", "defensive", "tempo"]),
        grip = random.choice(["french","pistol"])
    )

def generate_fencers(n):
    return [random_fencer(i) for i in range(n)]

#main
if __name__ == "__main__":
    fencers = generate_fencers(16)

    toc = time.time()

    winner = run_tournament(fencers)

    tic = time.time()

    print(f"\nWinner: {winner.name}")
    print(f"Winner Stats: {winner.style}, {winner.grip}")
    print(f"\nExecution Time: {tic - toc:.4f} seconds")


