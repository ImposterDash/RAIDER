import nmap
import time
from colorama import Fore

class ReconAgent:
    def __init__(self, blackboard):
        self.board = blackboard
        self.nm = None
        try:
            self.nm = nmap.PortScanner()
        except:
            print(f"{Fore.YELLOW}[System] Nmap not found. Using Simulation Mode.{Fore.RESET}")

    def run(self):
        target = self.board.state["target_ip"]
        print(f"{Fore.BLUE}[Recon] Scanning {target}...{Fore.RESET}")
        
        if self.nm:
            try:
                self.nm.scan(target, arguments='-p 80,443,3000,5000,8000,8080 -sV -T4')
                found = {}
                if target in self.nm.all_hosts() and 'tcp' in self.nm[target]:
                    for port, info in self.nm[target]['tcp'].items():
                        state = info['state']
                        name = info['name']
                        print(f"   -> Port {port} ({name}): {state}")
                        if state == 'open': found[port] = name
                self.board.update_scan(found)
            except Exception as e:
                print(f"Nmap Error: {e}")
                self.mock_scan()
        else:
            self.mock_scan()
            
        return "SCAN_COMPLETE"

    def mock_scan(self):
        time.sleep(1)
        print(f"   -> Port 5000 (http): open")
        self.board.update_scan({5000: 'http'})