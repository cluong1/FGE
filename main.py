import random
import time
from dataclasses import dataclass
from typing import List, Tuple
from multiprocessing import Pool, cpu_count


#FENCER MODEL
@dataclass
class Fencer:
    name: str
    style: str      #"aggressive", "defensive", "tempo"
    grip: str       #"french", "pistol"
    skill: float    # base skill level (0-1)
    """
    height
    gender
    age
    confidence
    weight
    
    """

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
    ("attack", "parry"): (-0.5, +0.5),
    ("attack", "feint"): (+0.5, -0.5),

    ("parry", "attack"): (+0.5, -0.5),
    ("parry", "parry"): (0.0, 0.0),
    ("parry", "feint"): (-0.5, +0.5),

    ("feint", "attack"): (-0.5, +0.5),
    ("feint", "parry"): (+0.5, -0.5),
    ("feint", "feint"): (0.0, 0.0),
}

def grip_modifier(f1: Fencer, f2: Fencer):
    mod1, mod2 = 0, 0

    # pistol = more control (better parry)
    # french = more reach (better attack)

    if f1.grip == "pistol":
        mod1 += 0.1
    if f2.grip == "pistol":
        mod2 += 0.1

    if f1.grip == "french":
        mod1 += 0.1
    if f2.grip == "french":
        mod2 += 0.1

    return mod1, mod2

#DOUBLE TOUCH CHANCE
def double_touch_chance(f1: Fencer, f2: Fencer):
    base = 0.05

    #French grips increase double touch chance
    if f1.grip == "french":
        base += 0.15
    if f2.grip == "french":
        base += 0.15

    #Defensive style decreases double touch chance
    if f1.style == "defensive":
        base -= 0.12
    if f2.style == "defensive":
        base -= 0.12

    #tempo style increases double touch chance
    if f1.style == "tempo":
        base += 0.12
    if f2.style == "tempo":
        base += 0.12

    return max(0.0, min(base,1.0))

#SINGLE TOUCH RESOLUTION
def resolve_touch(f1: Fencer, f2: Fencer) -> Tuple[int, int]:
    action1 = choose_action(f1)
    action2 = choose_action(f2)

    if random.random() < double_touch_chance(f1, f2):
        return 1, 1

    score1 = f1.skill
    score2 = f2.skill

    mod1, mod2 = INTERACTION_MATRIX[(action1, action2)]
    score1 += mod1
    score2 += mod2

    g1, g2 = grip_modifier(f1, f2)
    score1 += g1
    score2 += g2

    score1 = max(score1, 0.01)
    score2 = max(score2, 0.01)

    total = score1 + score2
    return (1, 0) if random.random() < (score1 / total) else (0, 1)
    
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

def run_tournament(fencers: List[Fencer], verbose=False) -> Fencer:
    round_num = 1

    while len(fencers) > 1:
        if verbose:
            print(f"Round {round_num}: {len(fencers)} fencers")
        fencers = run_round(fencers)
        round_num += 1

    return fencers[0]

# PARALLEL VERSION
def simulate_match(pair):
    f1, f2 = pair
    return simulate_bout(f1, f2)


def run_round_parallel(fencers: List[Fencer]) -> List[Fencer]:
    random.shuffle(fencers)
    pairs = [(fencers[i], fencers[i + 1]) for i in range(0, len(fencers), 2)]

    with Pool(cpu_count()) as p:
        winners = p.map(simulate_match, pairs)

    return winners

#GENERATION HELPER FUNCTIONS
def random_fencer(i: int) -> Fencer:
    return Fencer(
        name=f"Fencer_{i}",
        style=random.choice(["aggressive", "defensive", "tempo"]),
        grip=random.choice(["french", "pistol"]),
        skill=random.uniform(0.7, 1.3),
    )

def generate_fencers(n):
    return [random_fencer(i) for i in range(n)]

def benchmark(num_runs=5, num_fencers=64):
    times = []
    style_counts = {"aggressive": 0, "defensive": 0, "tempo": 0}
    grip_counts = {"french": 0, "pistol": 0}
    combo_counts = {} #Track (style, grip) pairs


    for _ in range(num_runs):
        fencers = generate_fencers(num_fencers)

        start = time.perf_counter()
        winner = run_tournament(fencers, verbose=False)
        end = time.perf_counter()

        times.append(end - start)

        # Track winner attributes
        style_counts[winner.style] += 1
        grip_counts[winner.grip] += 1

        # track combos
        combo = (winner.style, winner.grip)
        combo_counts[combo] = combo_counts.get(combo,0) + 1

    avg_time = sum(times) / len(times)

    print(f"\nRuns: {num_runs}")
    print(f"Average Time: {avg_time:.6f} seconds")
    print(f"Min Time: {min(times):.6f}")
    print(f"Max Time: {max(times):.6f}")

    print("\nWinner Style Distribution ")
    for style, count in style_counts.items():
        print(f"{style}: {count} ({count/num_runs:.2%})")

    print("\nWinner Grip Distribution ")
    for grip, count in grip_counts.items():
        print(f"{grip}: {count} ({count/num_runs:.2%})")

    print("\nWinner Style + Grip Combination Distribution")
    for combo, count in combo_counts.items():
        style, grip = combo
        print(f"{style} + {grip}: {count} ({count/num_runs:.2%})")

#main
if __name__ == "__main__":
    print("=== SINGLE RUN ===")
    fencers = generate_fencers(16)
    winner = run_tournament(fencers, verbose=True)
    print(f"Winner: {winner.name}")
    print(f"Winner Stats: {winner.style}, {winner.grip}\n")

    print("=== BENCHMARK ===")
    benchmark(num_runs=5, num_fencers=16384)
    benchmark(num_runs=5, num_fencers=64)
    benchmark(num_runs=5, num_fencers=256)

    

