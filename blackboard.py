import json
import datetime
from colorama import Fore, Style

class Blackboard:
    def __init__(self):
        self.state = {
            "target_ip": "",
            "target_url": "",
            "status": "IDLE",         
            "scanned": False,
            "ports": {},              
            "os_info": "Unknown",
            "mac_address": "Unknown",
            "topology": [],
            "network_vulns": [],
            "vulnerabilities": [],
            "credentials": [],        
            "flag_captured": False,
            "sqli_success": False,
            "xss_success": False,
            "activity_log": []
        }

    def log_event(self, source, event, details=""):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": timestamp,
            "source": source,
            "event": event,
            "details": details
        }
        self.state["activity_log"].append(entry)

    def update_scan(self, scan_data):
        if "ports" in scan_data: self.state["ports"] = scan_data["ports"]
        if "os" in scan_data: self.state["os_info"] = scan_data["os"]
        if "mac" in scan_data: self.state["mac_address"] = scan_data["mac"]
        if "hops" in scan_data: self.state["topology"] = scan_data["hops"]
        if "vulns" in scan_data: self.state["network_vulns"].extend(scan_data["vulns"])

        self.state["scanned"] = True
        
        self.log_event("ReconAgent", "Scan Data Updated", f"Found {len(self.state['ports'])} ports")
        
        print(f"\n{Fore.CYAN}[Blackboard] INTELLIGENCE UPDATE:{Fore.RESET}")
        print(f"   :: Open Ports: {list(self.state['ports'].keys())}")
        
        os_disp = self.state['os_info']
        if os_disp == "Unknown": os_disp = "Unknown (Cloud/Firewall Protected)"
            
        mac_disp = self.state['mac_address']
        if mac_disp == "Unknown": mac_disp = "Unknown (Remote Target - Layer 2 Hidden)"
            
        print(f"   :: OS Detected: {os_disp}")
        print(f"   :: MAC Address: {mac_disp}")

    def add_vuln(self, vuln_desc):
        self.state["vulnerabilities"].append(vuln_desc)
        self.log_event("Blackboard", "Vulnerability Confirmed", vuln_desc)
        print(f"{Fore.RED}[Blackboard] Vulnerability Logged: {vuln_desc}{Fore.RESET}")

    def set_flag(self, flag):
        self.state["flag_captured"] = True
        self.log_event("Blackboard", "OBJECTIVE COMPLETED", f"Flag: {flag}")
        print(f"\n{Fore.GREEN}[Blackboard] CRITICAL: Flag Captured -> {flag}{Fore.RESET}")

    def get_rl_state(self):
        has_http = any(s == 'http' or s == 'http-alt' for s in self.state["ports"].values())
        
        return (
            self.state["scanned"], 
            has_http, 
            self.state["sqli_success"], 
            self.state["xss_success"]
        )