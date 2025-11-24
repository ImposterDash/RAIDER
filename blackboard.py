import json
import datetime

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
        self.log_event("Blackboard", "Scan Data Updated", f"Found {len(self.state['ports'])} ports")
        
        print(f"\n[Blackboard] SCAN UPDATE:")
        print(f"   :: Open Ports: {list(self.state['ports'].keys())}")

    def add_vuln(self, vuln_desc):
        self.state["vulnerabilities"].append(vuln_desc)
        self.log_event("Blackboard", "Vulnerability Confirmed", vuln_desc)
        print(f"[Blackboard] Vulnerability Logged: {vuln_desc}")

    def set_flag(self, flag):
        self.state["flag_captured"] = True
        self.log_event("Blackboard", "OBJECTIVE COMPLETED", f"Flag: {flag}")
        print(f"\n[Blackboard] CRITICAL: Flag Captured -> {flag}")

    def get_rl_state(self):
        has_http = any(s == 'http' or s == 'http-alt' for s in self.state["ports"].values())
        has_vuln = len(self.state["vulnerabilities"]) > 0 or len(self.state["network_vulns"]) > 0
        return (self.state["scanned"], has_http, has_vuln, self.state["flag_captured"])