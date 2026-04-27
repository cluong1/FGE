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
    height: float   # in cm (160-200)
    age: int        # 16-40
    confidence: float   #starts ~1.0, changes over time

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

def choose_distance(f1, f2):
    weights = {
        "aggressive": [0.2, 0.3, 0.5],  # prefers close
        "defensive": [0.5, 0.3, 0.2],   # prefers long
        "tempo":     [0.3, 0.4, 0.3],   # neutral
    }

    d1 = weights[f1.style]
    d2 = weights[f2.style]

    combined = [(d1[i] + d2[i]) / 2 for i in range(3)]
    return random.choices(["long","mid", "short"], weights=combined)[0]

#height modifier
def height_modifier(f1: Fencer, f2: Fencer, action1, action2, distance):
    mod1, mod2 = 0.0, 0.0

    height_diff = f1.height - f2.height

    #long distance gives reach advantage to tall
    if distance == "long":
        if action1 =="attack":
            mod1 += 0.004 * height_diff
        if action2 == "attack":
            mod2 += -0.004 * height_diff

    #short distance gives inside advantage to short
    elif distance == "short":
        if action1 =="attack":
            mod1 += -0.004 * height_diff
        if action2 =="attack":
            mod2 += 0.004 * height_diff

    return mod1, mod2

#age modifier
def age_modifier(f: Fencer):
    #Peak ~25
    age_factor = (f.age -25) / 15

    confidence_boost = 0.05 * age_factor
    attack_penalty = -0.1 * max(age_factor, 0)

    return confidence_boost, attack_penalty



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
def resolve_touch(f1: Fencer, f2: Fencer, distance) -> Tuple[int, int]:

    action1 = choose_action(f1)
    action2 = choose_action(f2)

    if random.random() < double_touch_chance(f1, f2):
        return 1, 1

    score1 = f1.skill * f1.confidence
    score2 = f2.skill * f2.confidence

    mod1, mod2 = INTERACTION_MATRIX[(action1, action2)]
    score1 += mod1
    score2 += mod2

    #grip added
    g1, g2 = grip_modifier(f1, f2)
    score1 += g1
    score2 += g2

    #height added
    h1, h2 = height_modifier(f1,f2,action1,action2,distance)
    score1 +=h1
    score2 += h2

    #age added
    c1, a1 = age_modifier(f1)
    c2, a2 = age_modifier(f2)
    if action1 == "attack":
        score1 += a1
    if action2 == "attack":
        score2 += a2

    score1 += c1
    score2 += c2
    

    score1 = max(score1, 0.01)
    score2 = max(score2, 0.01)

    total = score1 + score2
    return (1, 0) if random.random() < (score1 / total) else (0, 1)
    
#BOUT LOGIC
def simulate_bout(f1: Fencer, f2: Fencer, target = 15):
    score1, score2 = 0, 0

    distance=choose_distance(f1,f2)


    while score1 < target and score2 <target:
        t1,t2 = resolve_touch(f1, f2,distance)
        score1 += t1
        score2 += t2

    #confidence update based on how much the fencer wins by
    diff = abs(score1 - score2)

    if score1 > score2:
        winner, loser = f1, f2
    else:
        winner, loser = f2, f1

    #big win is big boost
    winner.confidence += 0.02 * diff

    #close win = slight fatigue penalty
    if diff <= 2:
        winner.confidence -=0.05

    #clamp confidence -this part provided by ChatGPT
    winner.confidence = max(0.7, min(winner.confidence,1.5))
    loser.confidence = max(0.7, loser.confidence - 0.05)
    

    return winner

#TOURNAMENT LOGIC
def run_round(fencers: List[Fencer]) -> List[Fencer]:
    winners = []

    for i in range(0, len(fencers),2):
        winner = simulate_bout(fencers[i],fencers[i+1])
        winners.append(winner)

    return winners

def run_tournament(fencers: List[Fencer], parallel=False, verbose=False) -> Fencer:
    round_num = 1

    pool = Pool(cpu_count()) if parallel else None

    while len(fencers) > 1:
        if verbose:
            print(f"Round {round_num}: {len(fencers)} fencers")

        if parallel:
            fencers = run_round_parallel(fencers, pool)
        else:
            fencers = run_round(fencers)

        round_num += 1

    if pool:
        pool.close()
        pool.join()

    return fencers[0]

# PARALLEL VERSION
def simulate_match(pair):
    f1, f2 = pair
    return simulate_bout(f1, f2)

def run_round_parallel(fencers: List[Fencer], pool) -> List[Fencer]:
    random.shuffle(fencers)

    pairs = [
        (fencers[i], fencers[i + 1])
        for i in range(0, len(fencers), 2)
    ]

    return pool.map(simulate_match, pairs)
#GENERATION HELPER FUNCTIONS
def random_fencer(i: int) -> Fencer:
    return Fencer(
        name=f"Fencer_{i}",
        style=random.choice(["aggressive", "defensive", "tempo"]),
        grip=random.choice(["french", "pistol"]),
        skill=random.uniform(0.7, 1.3),
        height=random.uniform(160,200),
        age=random.randint(16,40),
        confidence=1.0
    )

def generate_fencers(n):
    return [random_fencer(i) for i in range(n)]

def benchmark_compare(num_runs=5, num_fencers=64):
    seq_times = []
    par_times = []

    for _ in range(num_runs):
        fencers_seq = generate_fencers(num_fencers)
        fencers_par = [f for f in fencers_seq]  # same input

        # Sequential
        start = time.perf_counter()
        run_tournament(fencers_seq, parallel=False)
        end = time.perf_counter()
        seq_times.append(end - start)

        # Parallel
        start = time.perf_counter()
        run_tournament(fencers_par, parallel=True)
        end = time.perf_counter()
        par_times.append(end - start)

    avg_seq = sum(seq_times) / num_runs
    avg_par = sum(par_times) / num_runs

    speedup = avg_seq / avg_par if avg_par > 0 else 0
    efficiency = speedup / cpu_count()

    #this benchmark was created by ChatGPT
    print(f"\n=== {num_runs} Tournaments === {num_fencers} Fencers ===")
    print(f"Sequential Avg: {avg_seq:.6f}s")
    print(f"Parallel Avg:   {avg_par:.6f}s")
    print(f"Speedup:        {speedup:.2f}x")
    print(f"Efficiency:     {efficiency:.2f}")
#main
if __name__ == "__main__":
    print("=== SINGLE SEQUENTIAL RUN ===")
    fencers = generate_fencers(16)
    winner = run_tournament(fencers, parallel=False)
    print(f"Winner: {winner.name}")
    print(f"Winner Stats: {winner.style}, {winner.grip}\n")

    print("=== SINGLE PARALLEL RUN ===")
    fencers = generate_fencers(16)
    winner = run_tournament(fencers, parallel=True)
    print(f"Winner: {winner.name}")
    print(f"Winner Stats: {winner.style}, {winner.grip}\n")

    print("=== PERFORMANCE COMPARISON ===\n")

    benchmark_compare(num_runs=5, num_fencers=64)
    benchmark_compare(num_runs=5, num_fencers=256)
    benchmark_compare(num_runs=5, num_fencers=4096)
    benchmark_compare(num_runs=5, num_fencers=16384)
    benchmark_compare(num_runs=5, num_fencers=65536)    


    

