import time
import numpy as np
import random
from blackboard import Blackboard
from coordination_core import CoordinationCore
from colorama import Fore, Style, init

init()

class MockReconAgent:
    def __init__(self, blackboard):
        self.board = blackboard

    def run(self):
        self.board.update_scan({5000: 'http', 22: 'ssh'})
        return "SCAN_COMPLETE"

class MockExploitAgent:
    def __init__(self, blackboard):
        self.board = blackboard

    def run(self):
        ports = self.board.state["ports"]
        if any('http' in s for s in ports.values()):
            if random.random() > 0.3: 
                self.board.set_flag("FLAG{TRAINING_DUMMY}")
                return "ATTACK_SUCCESS"
            else:
                return "ATTACK_FAILED"
        else:
            return "ATTACK_FAILED"

def train():
    print(f"{Fore.CYAN}=== STARTING ROBUST TRAINING SIMULATION ==={Fore.RESET}")
    dummy_board = Blackboard()
    commander = CoordinationCore(dummy_board)
    commander.epsilon = 0.6
    
    episodes = 100
    
    for episode in range(episodes):
        bb = Blackboard()
        commander.board = bb
        recon = MockReconAgent(bb)
        exploit = MockExploitAgent(bb)
        
        steps = 0
        total_reward = 0
        done = False
        
        if episode > 70: commander.epsilon = 0.95
        
        print(f"Episode {episode+1}: ", end="")
        
        while not done and steps < 15:
            steps += 1
            state = commander.get_state_key()
            action, action_idx = commander.choose_action()
            
            if action == "DEPLOY_RECON":
                recon.run()
            elif action == "DEPLOY_EXPLOIT":
                exploit.run()
            
            new_state = commander.get_state_key()
            reward = commander.calculate_reward(state, new_state, action)
            
            if state == new_state and action == "DEPLOY_EXPLOIT":
                reward -= 20 

            commander.learn(state, action_idx, reward, new_state)
            total_reward += reward
            
            if bb.state["flag_captured"]:
                done = True
                print(f"{Fore.GREEN}WIN{Fore.RESET} ({total_reward})", end="\r")
            
        if not bb.state["flag_captured"]:
            print(f"{Fore.RED}FAIL{Fore.RESET} ({total_reward})", end="\r")
            
        print("")

    print(f"\n{Fore.YELLOW}Training Complete.{Fore.RESET}")
    commander.save_brain()

if __name__ == "__main__":
    train()