import json

class Blackboard:
    def __init__(self):
        self.state = {
            "target_ip": "",
            "target_url": "",
            "status": "IDLE",         
            "scanned": False,
            "ports": {},              
            "vulnerabilities": [],    
            "credentials": [],        
            "flag_captured": False
        }

    def update_scan(self, ports_dict):
        self.state["ports"] = ports_dict
        self.state["scanned"] = True
        print(f"\n[Blackboard] Updated: Found Ports {list(ports_dict.keys())}")

    def add_vuln(self, vuln_desc):
        self.state["vulnerabilities"].append(vuln_desc)
        print(f"[Blackboard] Vulnerability Logged: {vuln_desc}")

    def set_flag(self, flag):
        self.state["flag_captured"] = True
        print(f"\n[Blackboard] CRITICAL: Flag Captured -> {flag}")

    def get_rl_state(self):
        has_http = any(s == 'http' or s == 'http-alt' for s in self.state["ports"].values())
        has_vuln = len(self.state["vulnerabilities"]) > 0
        return (self.state["scanned"], has_http, has_vuln, self.state["flag_captured"])