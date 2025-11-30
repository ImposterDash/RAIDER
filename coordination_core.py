import numpy as np
import pickle
import os
from colorama import Fore

class CoordinationCore:
    def __init__(self, blackboard):
        self.board = blackboard
        self.q_table = {} 
        self.actions = ["DEPLOY_RECON", "DEPLOY_SQLI", "DEPLOY_XSS", "WAIT"]
        self.lr = 0.1
        self.gamma = 0.9
        self.epsilon = 0.9
        self.filename = "mission_control.pkl"
        self.load_brain()

    def get_state_key(self):
        return self.board.get_rl_state()

    def choose_action(self):
        state = self.get_state_key()
        if state not in self.q_table:
            self.q_table[state] = np.zeros(len(self.actions))

        if np.random.uniform() < self.epsilon:
            action_idx = np.argmax(self.q_table[state])
        else:
            action_idx = np.random.choice(len(self.actions))
            
        return self.actions[action_idx], action_idx

    def learn(self, prev_state, action_idx, reward, new_state):
        if prev_state not in self.q_table: self.q_table[prev_state] = np.zeros(len(self.actions))
        if new_state not in self.q_table: self.q_table[new_state] = np.zeros(len(self.actions))
        
        q_predict = self.q_table[prev_state][action_idx]
        q_target = reward + self.gamma * np.max(self.q_table[new_state])
        
        self.q_table[prev_state][action_idx] += self.lr * (q_target - q_predict)
        self.save_brain()

    def calculate_reward(self, prev_state, new_state, action):
        """
        State structure: (scanned, has_http, sqli_success, xss_success)
        Indices:         0        1         2             3
        """
        reward = -1
        
        # 1. Reward for NEW SQLi Success
        if new_state[2] and not prev_state[2]:
            return 100 

        # 2. Reward for NEW XSS Success
        if new_state[3] and not prev_state[3]:
            return 100 
            
        # 3. Reward for Recon completion
        if new_state[0] and not prev_state[0] and action == "DEPLOY_RECON":
            return 10
            
        # 4. Punish attacking before Recon
        if (action == "DEPLOY_SQLI" or action == "DEPLOY_XSS") and not prev_state[0]:
            return -50

        # 5. Punish Recon if already scanned
        if action == "DEPLOY_RECON" and prev_state[0]:
            return -10

        # 6. Punish Repeating Attacks (If SQLi is already done, don't do it again)
        if action == "DEPLOY_SQLI" and prev_state[2]:
            return -50
            
        if action == "DEPLOY_XSS" and prev_state[3]:
            return -50

        # 7. Punish Waiting
        if action == "WAIT":
            return -2

        return reward

    def save_brain(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(self.q_table, f)

    def load_brain(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'rb') as f:
                    data = pickle.load(f)
                    first_key = next(iter(data))
                    # Basic integrity check
                    if len(data[first_key]) == len(self.actions):
                        self.q_table = data
                    else:
                        print(f"{Fore.YELLOW}[System] Brain architecture changed. Resetting memory.{Fore.RESET}")
            except:
                pass