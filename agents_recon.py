import nmap
import time
import socket
from colorama import Fore

class ReconAgent:
    def __init__(self, blackboard):
        self.board = blackboard
        self.nm = None
        try:
            self.nm = nmap.PortScanner()
        except:
            print(f"{Fore.YELLOW}[System] Nmap not found. Falling back to Simulation Mode.{Fore.RESET}")

    def run(self):
        target = self.board.state["target_ip"]
        print(f"{Fore.BLUE}[Recon] Starting FAST Scan on {target}...{Fore.RESET}")
        
        if self.nm:
            try:
                arguments = (
                    '-p 80,443,3000,5000,8000,8080 '
                    '-sV -O -T5 --max-retries 1 --script-timeout 10s '
                    '--script=http-sql-injection,http-methods,http-title,http-headers' 
                )
                
                try:
                    self.nm.scan(target, arguments=arguments)
                except nmap.PortScannerError:
                    print(f"{Fore.YELLOW}[Recon] Root privileges missing. Retrying without OS Detect...{Fore.RESET}")
                    fallback_args = arguments.replace("-O ", "")
                    self.nm.scan(target, arguments=fallback_args)

                scan_results = {
                    "ports": {},
                    "os": "Unknown",
                    "mac": "Unknown",
                    "hops": [],
                    "vulns": []
                }

                if target in self.nm.all_hosts():
                    host_data = self.nm[target]

                    if 'tcp' in host_data:
                        for port, info in host_data['tcp'].items():
                            state = info['state']
                            name = info['name']
                            version = info.get('version', '')
                            product = info.get('product', '')
                            
                            print(f"   -> Port {port}: {state} | {product} {version}")
                            if state == 'open': 
                                scan_results["ports"][port] = name
                                
                                if 'script' in info:
                                    for script_id, output in info['script'].items():
                                        clean_output = output.strip().replace('\n', ' ')[:60]
                                        print(f"      [!] {script_id}: {clean_output}...")
                                        scan_results["vulns"].append(f"Port {port}: {script_id}")

                    if 'osmatch' in host_data and host_data['osmatch']:
                        best_match = host_data['osmatch'][0]
                        scan_results["os"] = f"{best_match['name']} ({best_match['accuracy']}% accuracy)"
                    
                    if 'addresses' in host_data and 'mac' in host_data['addresses']:
                        scan_results["mac"] = host_data['addresses']['mac']
                        if 'vendor' in host_data and scan_results["mac"] in host_data['vendor']:
                             scan_results["mac"] += f" ({host_data['vendor'][scan_results['mac']]})"

                self.board.update_scan(scan_results)

            except Exception as e:
                print(f"{Fore.RED}[Recon] Nmap Error: {e}{Fore.RESET}")
                self.mock_scan()
        else:
            self.mock_scan()
            
        return "SCAN_COMPLETE"

    def mock_scan(self):
        time.sleep(1)
        print(f"   -> Port 5000 (http): open | Werkzeug httpd 2.0.2")
        print(f"   -> OS Detected: Linux 5.4 (Ubuntu)")
        print(f"   -> Vulnerability: http-sql-injection (Possible)")
        
        mock_data = {
            "ports": {5000: 'http', 22: 'ssh'},
            "os": "Linux Kernel 5.x (Ubuntu)",
            "mac": "00:1A:2B:3C:4D:5E (VirtualBox)",
            "hops": ["192.168.1.1"],
            "vulns": ["http-sql-injection"]
        }
        self.board.update_scan(mock_data)