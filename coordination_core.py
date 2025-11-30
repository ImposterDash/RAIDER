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
        reward = -1
        
        if new_state[2] and not prev_state[2]:
            return 100 

        if new_state[3] and not prev_state[3]:
            return 100 
            
        if new_state[0] and not prev_state[0] and action == "DEPLOY_RECON":
            return 10
            
        if (action == "DEPLOY_SQLI" or action == "DEPLOY_XSS") and not prev_state[0]:
            return -50

        if action == "DEPLOY_RECON" and prev_state[0]:
            return -10

        if action == "DEPLOY_SQLI" and prev_state[2]:
            return -50
            
        if action == "DEPLOY_XSS" and prev_state[3]:
            return -50

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
                    if len(data[first_key]) == len(self.actions):
                        self.q_table = data
                    else:
                        print(f"{Fore.YELLOW}[System] Brain architecture changed. Resetting memory.{Fore.RESET}")
            except:
                pass