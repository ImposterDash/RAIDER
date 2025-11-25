import time
import numpy as np
import random
import os
from blackboard import Blackboard
from coordination_core import CoordinationCore
from colorama import Fore, Style, init

init()

class MockReconAgent:
    def __init__(self, blackboard):
        self.board = blackboard

    def run(self):
        scan_data = {
            "ports": {5000: 'http', 22: 'ssh'},
            "os": "Linux (Mock)",
            "mac": "AA:BB:CC:DD:EE:FF"
        }
        self.board.update_scan(scan_data)
        return "SCAN_COMPLETE"

class MockSQLIAgent:
    def __init__(self, blackboard):
        self.board = blackboard

    def run(self):
        ports = self.board.state["ports"]
        if any('http' in s for s in ports.values()):
            if random.random() > 0.3: 
                self.board.set_flag("FLAG{TRAINING_SQLI_DUMMY}")
                return "ATTACK_SUCCESS"
            else:
                return "ATTACK_FAILED"
        else:
            return "ATTACK_FAILED"

class MockXSSAgent:
    def __init__(self, blackboard):
        self.board = blackboard

    def run(self):
        ports = self.board.state["ports"]
        if any('http' in s for s in ports.values()):
            if random.random() > 0.3: 
                self.board.add_vuln("Reflected XSS found (Simulated)")
                self.board.set_flag("FLAG{TRAINING_XSS_DUMMY}")
                return "ATTACK_SUCCESS"
            else:
                return "ATTACK_FAILED"
        else:
            return "ATTACK_FAILED"

def train():
    print(f"{Fore.CYAN}=== STARTING ROBUST TRAINING SIMULATION (SQLi + XSS) ==={Fore.RESET}")
    
    if os.path.exists("mission_control.pkl"):
        print(f"{Fore.YELLOW}[System] Note: Using existing brain. If behavior is poor, delete 'mission_control.pkl' and retry.{Fore.RESET}")

    dummy_board = Blackboard()
    commander = CoordinationCore(dummy_board)
    commander.epsilon = 0.6
    
    episodes = 200 
    
    for episode in range(episodes):
        bb = Blackboard()
        commander.board = bb
        
        recon = MockReconAgent(bb)
        sqli = MockSQLIAgent(bb)
        xss = MockXSSAgent(bb)
        
        steps = 0
        total_reward = 0
        done = False
        
        if episode > 50: commander.epsilon = 0.8
        if episode > 100: commander.epsilon = 0.9
        if episode > 150: commander.epsilon = 0.98
        
        print(f"Episode {episode+1}: ", end="")
        
        while not done and steps < 20:
            steps += 1
            state = commander.get_state_key()
            action, action_idx = commander.choose_action()
            
            if action == "DEPLOY_RECON":
                recon.run()
            elif action == "DEPLOY_SQLI":
                sqli.run()
            elif action == "DEPLOY_XSS":
                xss.run()
            elif action == "WAIT":
                pass
            
            new_state = commander.get_state_key()
            reward = commander.calculate_reward(state, new_state, action)
            
            if state == new_state and (action == "DEPLOY_SQLI" or action == "DEPLOY_XSS"):
                reward -= 10 

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
    print(f"{Fore.CYAN}Brain saved to 'mission_control.pkl'{Fore.RESET}")

if __name__ == "__main__":
    train()