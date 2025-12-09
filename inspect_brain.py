import pickle
import numpy as np
import os
from colorama import Fore, init

init()

filename = "mission_control.pkl"

if not os.path.exists(filename):
    print(f"{Fore.RED}No brain file found ({filename}). Run train_manager.py first.{Fore.RESET}")
    exit()

with open(filename, "rb") as f:
    q_table = pickle.load(f)

actions = ["DEPLOY_RECON", "DEPLOY_SQLI", "DEPLOY_XSS", "WAIT"]

print(f"\n{Fore.CYAN}=== REINFORCEMENT LEARNING BRAIN ==={Fore.RESET}")
print(f"{'STATE (Scan?, HTTP?, SQLi?, XSS?)':<40} | {'BEST ACTION':<15} | {'VALUES (Recon, SQLi, XSS, Wait)'}")
print("-" * 110)

sorted_states = sorted(q_table.keys(), key=lambda x: str(x))

for state in sorted_states:
    values = q_table[state]
    
    if len(values) != len(actions):
        print(f"{str(state):<40} | {Fore.RED}CORRUPT/OLD{Fore.RESET}   | {values}")
        continue

    best_action_idx = np.argmax(values)
    best_action = actions[best_action_idx]
    
    action_color = Fore.WHITE
    if best_action == "DEPLOY_RECON": action_color = Fore.BLUE
    elif best_action == "DEPLOY_SQLI": action_color = Fore.RED
    elif best_action == "DEPLOY_XSS": action_color = Fore.MAGENTA
    elif best_action == "WAIT": action_color = Fore.YELLOW

    state_str = str(state)
    values_str = ", ".join([f"{v:.1f}" for v in values])
    
    print(f"{state_str:<40} | {action_color}{best_action:<15}{Fore.RESET} | [{values_str}]")

print("-" * 110)
print(f"Total learned states: {len(q_table)}")