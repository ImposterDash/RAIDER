import threading
import time
import os
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv
from mock_target import run_server
from blackboard import Blackboard
from coordination_core import CoordinationCore
from agents_recon import ReconAgent
from agents_exploit import ExploitAgent
from reporting import Reporter
from colorama import Fore, Style, init

init()
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def resolve_target(user_input):
    print(f"{Fore.CYAN}[System] Resolving Target: '{user_input}'...{Fore.RESET}")
    target = user_input.strip()
    
    hostname = target
    if "://" in target:
        parsed = urlparse(target)
        hostname = parsed.netloc.split(':')[0]
    else:
        hostname = target.split('/')[0].split(':')[0]

    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"{Fore.GREEN}[System] DNS Resolution: {hostname} -> {ip_address}{Fore.RESET}")
        return ip_address
    except socket.gaierror:
        print(f"{Fore.RED}[Error] Could not resolve hostname '{hostname}'.{Fore.RESET}")
        return None

def main():
    if not API_KEY:
        print("❌ ERROR: Please add GEMINI_API_KEY to .env file")
        return

    print(f"{Fore.YELLOW}=== RAIDER MISSION CONTROL ==={Fore.RESET}")
    user_input = input("Enter Target URL (or press Enter for Localhost): ")

    target_ip = "127.0.0.1"
    target_url = "http://127.0.0.1:5000"

    if user_input:
        target_ip = resolve_target(user_input)
        target_url = user_input
        if not target_ip: return
    else:
        print(f"{Fore.BLUE}[System] Launching Local Mock Server...{Fore.RESET}")
        server = threading.Thread(target=run_server)
        server.daemon = True
        server.start()
        time.sleep(1)

    bb = Blackboard()
    bb.state["target_ip"] = target_ip 
    bb.state["target_url"] = target_url
    
    commander = CoordinationCore(bb)
    recon_team = ReconAgent(bb)
    exploit_team = ExploitAgent(bb, API_KEY)

    print(f"{Fore.YELLOW}=== MISSION STARTING AGAINST {target_url} ==={Fore.RESET}")
    
    sqli_failures = 0
    xss_failures = 0
    MAX_FAILURES = 3

    for step in range(30):
        print(f"\n--- Mission Step {step+1} ---")
        
        current_state_key = commander.get_state_key()
        action_name, action_idx = commander.choose_action()
        print(f"{Fore.MAGENTA}[Commander] Decision: {action_name}{Fore.RESET}")
        
        result = "WAIT"
        
        if action_name == "DEPLOY_RECON":
            result = recon_team.run()
            
        elif action_name == "DEPLOY_SQLI":
            if bb.state["sqli_success"]:
                result = "ALREADY_SUCCESS"
            elif sqli_failures >= MAX_FAILURES:
                print(f"{Fore.YELLOW}[System] Skipping SQLi (Max failures reached).{Fore.RESET}")
                result = "SKIPPED"
            else:
                result = exploit_team.run() 
                if result in ["FAILED", "NO_TARGET", "ERROR"]:
                    sqli_failures += 1
            
        elif action_name == "DEPLOY_XSS":
            if bb.state["xss_success"]:
                result = "ALREADY_SUCCESS"
            elif xss_failures >= MAX_FAILURES:
                print(f"{Fore.YELLOW}[System] Skipping XSS (Max failures reached).{Fore.RESET}")
                result = "SKIPPED"
            else:
                result = exploit_team.run_xss()
                if result in ["FAILED", "NO_TARGET", "ERROR"]:
                    xss_failures += 1
            
        elif action_name == "WAIT":
            print("Standing by...")

        new_state_key = commander.get_state_key()
        reward = commander.calculate_reward(current_state_key, new_state_key, action_name)
        
        if result == "SKIPPED":
            reward = -100
            
        commander.learn(current_state_key, action_idx, reward, new_state_key)
        
        sqli_status = 'DONE' if bb.state['sqli_success'] else ('GIVEN UP' if sqli_failures >= MAX_FAILURES else 'PENDING')
        xss_status = 'DONE' if bb.state['xss_success'] else ('GIVEN UP' if xss_failures >= MAX_FAILURES else 'PENDING')
        
        stats = f"Reward: {reward} | SQLi: {sqli_status} | XSS: {xss_status}"
        print(f"[RL] {stats}")
        
        sqli_finished = bb.state["sqli_success"] or sqli_failures >= MAX_FAILURES
        xss_finished = bb.state["xss_success"] or xss_failures >= MAX_FAILURES
        
        if sqli_finished and xss_finished:
            print(f"\n{Fore.GREEN}MISSION CONCLUDED (All objectives attempted or completed).{Fore.RESET}")
            break
            
        time.sleep(1)

    print(f"\n{Fore.CYAN}[System] Generating Mission Report...{Fore.RESET}")
    reporter = Reporter(bb)
    report_file = reporter.generate_report()
    print(f"{Fore.GREEN}[System] Report saved to: {report_file}{Fore.RESET}")

if __name__ == "__main__":
    main()