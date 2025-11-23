import pickle
import numpy as np

# Load the saved brain
with open("mission_control.pkl", "rb") as f:
    q_table = pickle.load(f)

actions = ["DEPLOY_RECON", "DEPLOY_EXPLOIT", "WAIT"]

print(f"{'STATE (Scanned?, HTTP?, Vuln?, Flag?)':<40} | {'BEST ACTION':<15} | {'VALUES'}")
print("-" * 80)

for state, values in q_table.items():
    best_action_idx = np.argmax(values)
    best_action = actions[best_action_idx]
    
    # Format state for readability
    state_str = str(state)
    
    print(f"{state_str:<40} | {best_action:<15} | {np.round(values, 1)}")