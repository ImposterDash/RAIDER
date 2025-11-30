import customtkinter as ctk
import threading
import time
import os
import sys
import socket
import re
import subprocess
import platform
from urllib.parse import urlparse
from dotenv import load_dotenv
from tkinter import END

# Import RAIDER Modules
from mock_target import run_server
from blackboard import Blackboard
from coordination_core import CoordinationCore
from agents_recon import ReconAgent
from agents_exploit import ExploitAgent
from reporting import Reporter

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class TextRedirector:
    """Redirects stdout/stderr to a Tkinter Text widget"""
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, string):
        if not string: return
        
        # FIX: Handle bytes input (common with Flask/Click output)
        if isinstance(string, bytes):
            try:
                string = string.decode('utf-8', errors='replace')
            except:
                string = str(string)

        clean_str = self.ansi_escape.sub('', string)
        try:
            # Schedule update on main thread to prevent crashing
            self.widget.after(0, self._append_text, clean_str)
        except:
            pass

    def _append_text(self, string):
        try:
            self.widget.configure(state="normal")
            self.widget.insert("end", string)
            self.widget.see("end")
            self.widget.configure(state="disabled")
        except:
            pass

    def flush(self):
        pass

class MissionThread(threading.Thread):
    def __init__(self, app, target_input):
        super().__init__()
        self.app = app
        self.target_input = target_input
        self.daemon = True
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set() # Set to True means "Running", False means "Paused"

    def resolve_target(self, user_input):
        print(f"[System] Resolving Target: '{user_input}'...")
        target = user_input.strip()
        hostname = target
        
        if "://" in target:
            parsed = urlparse(target)
            hostname = parsed.netloc.split(':')[0]
        else:
            hostname = target.split('/')[0].split(':')[0]

        try:
            ip_address = socket.gethostbyname(hostname)
            print(f"[System] DNS Resolution: {hostname} -> {ip_address}")
            return ip_address
        except socket.gaierror:
            print(f"[Error] Could not resolve hostname '{hostname}'.")
            return None

    def run(self):
        # 1. Setup Target
        target_ip = "127.0.0.1"
        target_url = "http://127.0.0.1:5000"

        if self.target_input:
            target_ip = self.resolve_target(self.target_input)
            target_url = self.target_input
            if not target_ip: 
                self.app.mission_running = False
                self.app.reset_ui_state()
                return
        else:
            print("[System] Launching Local Mock Server...")
            try:
                server = threading.Thread(target=run_server)
                server.daemon = True
                server.start()
                time.sleep(1)
            except Exception as e:
                print(f"[Warning] Server start issue (might be already running): {e}")

        # 2. Initialize Blackboard & Agents
        bb = Blackboard()
        bb.state["target_ip"] = target_ip 
        bb.state["target_url"] = target_url
        
        self.app.blackboard = bb
        
        commander = CoordinationCore(bb)
        recon_team = ReconAgent(bb)
        exploit_team = ExploitAgent(bb, API_KEY)

        print(f"=== MISSION STARTING AGAINST {target_url} ===")
        
        sqli_failures = 0
        xss_failures = 0
        MAX_FAILURES = 3

        # 3. Mission Loop
        for step in range(30):
            # Check Stop
            if self.stop_event.is_set():
                print(f"\n[System] Mission Terminated by User.")
                break
                
            # Check Pause
            if not self.pause_event.is_set():
                print(f"[System] Mission Paused. Waiting for resume...")
                self.app.update_status_labels("PAUSED")
                self.pause_event.wait() # Blocks here until set() is called
                print(f"[System] Mission Resumed.")
                
                # Double check stop in case we terminated while paused
                if self.stop_event.is_set(): 
                    print(f"\n[System] Mission Terminated by User.")
                    break

            self.app.update_progress("step", step+1)
            print(f"\n--- Mission Step {step+1} ---")
            
            current_state_key = commander.get_state_key()
            action_name, action_idx = commander.choose_action()
            
            print(f"[Commander] Decision: {action_name}")
            self.app.highlight_action(action_name)
            
            result = "WAIT"
            
            if action_name == "DEPLOY_RECON":
                if bb.state["scanned"]:
                    print("[System] Skipping Recon (Already Scanned).")
                    result = "SKIPPED"
                else:
                    self.app.update_status("Recon", "Scanning...")
                    result = recon_team.run()
                    self.app.update_status("Recon", "Complete")
                    self.app.refresh_intel() 
                
            elif action_name == "DEPLOY_SQLI":
                if bb.state["sqli_success"]:
                    result = "ALREADY_SUCCESS"
                elif sqli_failures >= MAX_FAILURES:
                    print("[System] Skipping SQLi (Max failures reached).")
                    result = "SKIPPED"
                else:
                    self.app.update_status("SQLi", "Attacking...")
                    result = exploit_team.run()
                    if result == "SUCCESS":
                        self.app.update_status("SQLi", "Pwned!")
                    elif result in ["FAILED", "NO_TARGET", "ERROR"]:
                        self.app.update_status("SQLi", "Failed")
                        sqli_failures += 1
                
            elif action_name == "DEPLOY_XSS":
                if bb.state["xss_success"]:
                    result = "ALREADY_SUCCESS"
                elif xss_failures >= MAX_FAILURES:
                    print("[System] Skipping XSS (Max failures reached).")
                    result = "SKIPPED"
                else:
                    self.app.update_status("XSS", "Injecting...")
                    result = exploit_team.run_xss()
                    if result == "SUCCESS":
                        self.app.update_status("XSS", "Executed!")
                    elif result in ["FAILED", "NO_TARGET", "ERROR"]:
                        self.app.update_status("XSS", "Failed")
                        xss_failures += 1
                
            elif action_name == "WAIT":
                print("Standing by...")

            new_state_key = commander.get_state_key()
            reward = commander.calculate_reward(current_state_key, new_state_key, action_name)
            
            if result == "SKIPPED":
                reward = -100
                
            commander.learn(current_state_key, action_idx, reward, new_state_key)
            self.app.update_metric("Reward", reward)
            self.app.refresh_intel()
            
            sqli_finished = bb.state["sqli_success"] or sqli_failures >= MAX_FAILURES
            xss_finished = bb.state["xss_success"] or xss_failures >= MAX_FAILURES
            
            if sqli_finished and xss_finished:
                print(f"MISSION CONCLUDED (All objectives attempted or completed).")
                break
                
            time.sleep(1)

        print("[System] Generating Mission Report...")
        reporter = Reporter(bb)
        report_file = reporter.generate_report()
        print(f"[System] Report saved to: {report_file}")
        
        # Trigger UI update on main thread
        self.app.after(0, lambda: self.app.on_mission_complete(report_file))
        
        self.app.mission_running = False
        self.app.reset_ui_state()

class RaiderDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RAIDER | Autonomous AI Red Teaming System")
        self.geometry("1200x800")
        
        # Maximize Window by default (Platform specific)
        self.after(0, lambda: self.state('zoomed') if sys.platform == 'win32' else self.attributes('-zoomed', True))
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.mission_running = False
        self.is_paused = False
        self.blackboard = None
        self.thread = None
        self.current_report = None
        
        # Define Colors
        self.col_active_green = "#008000"
        self.col_active_orange = "#FFA500"
        self.col_active_blue = "#1E90FF"
        self.col_active_red = "#8B0000"
        self.col_active_purple = "#800080"
        self.col_disabled = "#333333" # Dark Charcoal for better contrast than default gray

        self.setup_sidebar()
        self.setup_main_area()
        self.setup_right_panel()
        
        # Redirect stdout/stderr globally
        sys.stdout = TextRedirector(self.console_text)
        sys.stderr = TextRedirector(self.console_text)

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(11, weight=1) # Spacer at bottom

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="RAIDER\nCOMMAND", font=ctk.CTkFont(family="Consolas", size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Input Group
        self.target_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Target URL", font=ctk.CTkFont(family="Consolas", size=12))
        self.target_entry.grid(row=1, column=0, padx=20, pady=(0, 5))
        
        self.target_hint = ctk.CTkLabel(self.sidebar_frame, text="(Leave empty for Local Mock)", text_color="gray", font=ctk.CTkFont(size=10))
        self.target_hint.grid(row=2, column=0, padx=20, pady=(0, 20))

        # --- CONTROLS ---
        self.start_button = ctk.CTkButton(self.sidebar_frame, text="▶ DEPLOY MISSION", command=self.start_mission, fg_color=self.col_active_green, hover_color="#006400", font=ctk.CTkFont(weight="bold"))
        self.start_button.grid(row=3, column=0, padx=20, pady=5)
        
        # Separator line
        self.sep = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#2b2b2b")
        self.sep.grid(row=4, column=0, padx=20, pady=15, sticky="ew")

        self.pause_button = ctk.CTkButton(self.sidebar_frame, text="⏸ PAUSE", command=self.pause_mission, state="disabled", fg_color=self.col_disabled, text_color="white")
        self.pause_button.grid(row=5, column=0, padx=20, pady=5)
        
        self.resume_button = ctk.CTkButton(self.sidebar_frame, text="⏯ RESUME", command=self.resume_mission, state="disabled", fg_color=self.col_disabled)
        self.resume_button.grid(row=6, column=0, padx=20, pady=5)
        
        self.term_button = ctk.CTkButton(self.sidebar_frame, text="⏹ TERMINATE", command=self.terminate_mission, state="disabled", fg_color=self.col_disabled)
        self.term_button.grid(row=7, column=0, padx=20, pady=(5, 30))

        # --- REPORT BUTTON ---
        self.report_btn = ctk.CTkButton(self.sidebar_frame, text="📄 VIEW REPORT", command=self.open_report, state="disabled", fg_color=self.col_disabled)
        self.report_btn.grid(row=8, column=0, padx=20, pady=(0, 20))

        # --- STATUS ---
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.status_frame.grid(row=9, column=0, padx=20, sticky="w")
        
        self.status_label_1 = ctk.CTkLabel(self.status_frame, text="Recon Agent: IDLE", text_color="gray", font=ctk.CTkFont(family="Consolas", size=12))
        self.status_label_1.pack(anchor="w", pady=2)
        
        self.status_label_2 = ctk.CTkLabel(self.status_frame, text="SQLi Agent: IDLE", text_color="gray", font=ctk.CTkFont(family="Consolas", size=12))
        self.status_label_2.pack(anchor="w", pady=2)
        
        self.status_label_3 = ctk.CTkLabel(self.status_frame, text="XSS Agent: IDLE", text_color="gray", font=ctk.CTkFont(family="Consolas", size=12))
        self.status_label_3.pack(anchor="w", pady=2)

    def setup_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Top Stats Cards Container
        self.stats_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.stats_container.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.stats_container.grid_columnconfigure((0,1,2), weight=1)

        # Card 1: Step
        self.card_step = ctk.CTkFrame(self.stats_container, height=60, corner_radius=10, fg_color="#1f1f1f")
        self.card_step.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.stat_step = ctk.CTkLabel(self.card_step, text="STEP: 0/30", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.stat_step.place(relx=0.5, rely=0.5, anchor="center")

        # Card 2: Reward
        self.card_reward = ctk.CTkFrame(self.stats_container, height=60, corner_radius=10, fg_color="#1f1f1f")
        self.card_reward.grid(row=0, column=1, sticky="ew", padx=10)
        self.stat_reward = ctk.CTkLabel(self.card_reward, text="REWARD: 0", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.stat_reward.place(relx=0.5, rely=0.5, anchor="center")

        # Card 3: Action
        self.card_action = ctk.CTkFrame(self.stats_container, height=60, corner_radius=10, fg_color="#1f1f1f")
        self.card_action.grid(row=0, column=2, sticky="ew", padx=(10, 0))
        self.current_action = ctk.CTkLabel(self.card_action, text="WAITING", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color="#00BFFF")
        self.current_action.place(relx=0.5, rely=0.5, anchor="center")

        # Console
        self.console_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.console_frame.grid(row=1, column=0, sticky="nsew")
        
        self.console_label = ctk.CTkLabel(self.console_frame, text="MISSION LOGS", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.console_label.pack(anchor="w", padx=10, pady=(10,0))
        
        self.console_text = ctk.CTkTextbox(self.console_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.console_text.pack(expand=True, fill="both", padx=10, pady=10)
        self.console_text.configure(state="disabled")

    def setup_right_panel(self):
        self.right_frame = ctk.CTkFrame(self, width=350, corner_radius=0)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 0))
        
        self.intel_label = ctk.CTkLabel(self.right_frame, text="INTELLIGENCE", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"))
        self.intel_label.pack(pady=20)
        
        self.intel_text = ctk.CTkTextbox(self.right_frame, width=300, height=500, font=ctk.CTkFont(family="Consolas", size=11))
        self.intel_text.pack(padx=10, pady=10, fill="both", expand=True)
        self.intel_text.insert("0.0", "Waiting for Recon...")
        self.intel_text.configure(state="disabled")

    # --- ACTION HANDLERS ---
    
    def start_mission(self):
        if self.mission_running: return
        
        target = self.target_entry.get()
        self.mission_running = True
        self.is_paused = False
        self.current_report = None
        
        # Enable controls, set colors for Active state
        self.start_button.configure(state="disabled", text="MISSION ACTIVE", fg_color=self.col_disabled)
        
        self.pause_button.configure(state="normal", fg_color=self.col_active_orange)
        self.resume_button.configure(state="disabled", fg_color=self.col_disabled)
        self.term_button.configure(state="normal", fg_color=self.col_active_red)
        
        self.report_btn.configure(state="disabled", fg_color=self.col_disabled)
        self.target_entry.configure(state="disabled")
        
        self.console_text.configure(state="normal")
        self.console_text.delete("0.0", END)
        self.console_text.configure(state="disabled")
        
        self.thread = MissionThread(self, target)
        self.thread.start()

    def pause_mission(self):
        if self.thread and self.mission_running and not self.is_paused:
            self.thread.pause_event.clear()
            self.is_paused = True
            
            # Switch Colors to indicate State
            self.pause_button.configure(state="disabled", fg_color=self.col_disabled)
            self.resume_button.configure(state="normal", fg_color=self.col_active_blue)
            
            print("\n[UI] Requesting Pause...")

    def resume_mission(self):
        if self.thread and self.is_paused:
            self.thread.pause_event.set()
            self.is_paused = False
            
            # Switch Colors back
            self.pause_button.configure(state="normal", fg_color=self.col_active_orange)
            self.resume_button.configure(state="disabled", fg_color=self.col_disabled)
            
            self.update_status_labels("RESUMED")

    def terminate_mission(self):
        if self.thread and self.mission_running:
            print("\n[UI] Terminate Signal Sent! Stopping after current step...")
            self.thread.stop_event.set()
            if not self.thread.pause_event.is_set():
                self.thread.pause_event.set()
            
            self.start_button.configure(text="STOPPING...", fg_color="darkred")
            self.pause_button.configure(state="disabled", fg_color=self.col_disabled)
            self.resume_button.configure(state="disabled", fg_color=self.col_disabled)
            self.term_button.configure(state="disabled", fg_color=self.col_disabled)

    def on_mission_complete(self, report_path):
        """Called by thread when report is ready"""
        self.current_report = report_path
        self.report_btn.configure(state="normal", fg_color=self.col_active_purple)
        print(f"[UI] Report ready: {report_path}")

    def open_report(self):
        """Opens the PDF report using the default OS application"""
        if not self.current_report: return
        
        try:
            path = os.path.abspath(self.current_report)
            if platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', path))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(path)
            else:                                   # Linux
                subprocess.call(('xdg-open', path))
        except Exception as e:
            print(f"[Error] Could not open report: {e}")

    def reset_ui_state(self):
        self.after(0, self._reset_ui_internal)

    def _reset_ui_internal(self):
        self.start_button.configure(state="normal", text="▶ DEPLOY MISSION", fg_color=self.col_active_green)
        self.pause_button.configure(state="disabled", fg_color=self.col_disabled)
        self.resume_button.configure(state="disabled", fg_color=self.col_disabled)
        self.term_button.configure(state="disabled", fg_color=self.col_disabled)
        self.target_entry.configure(state="normal")
        self.current_action.configure(text="WAITING", text_color="#00BFFF")
        self.update_status_labels("IDLE")

    # --- UPDATE HELPERS ---

    def update_status_labels(self, status):
        if status == "IDLE":
            self.status_label_1.configure(text="Recon Agent: IDLE", text_color="gray")
            self.status_label_2.configure(text="SQLi Agent: IDLE", text_color="gray")
            self.status_label_3.configure(text="XSS Agent: IDLE", text_color="gray")
        elif status == "PAUSED":
            self.current_action.configure(text="PAUSED", text_color="yellow")

    def update_status(self, agent, status):
        color = "gray"
        if status in ["Scanning...", "Attacking...", "Injecting..."]: color = "yellow"
        if status in ["Complete", "Pwned!", "Executed!"]: color = "#00FF00" 
        if status == "Failed": color = "red"
        
        if agent == "Recon":
            self.status_label_1.configure(text=f"Recon: {status}", text_color=color)
        elif agent == "SQLi":
            self.status_label_2.configure(text=f"SQLi: {status}", text_color=color)
        elif agent == "XSS":
            self.status_label_3.configure(text=f"XSS: {status}", text_color=color)

    def highlight_action(self, action):
        self.current_action.configure(text=f"{action}")
        if action == "DEPLOY_RECON": self.current_action.configure(text_color="#00BFFF") 
        elif action == "DEPLOY_SQLI": self.current_action.configure(text_color="#FF4500") 
        elif action == "DEPLOY_XSS": self.current_action.configure(text_color="#FF00FF") 
        else: self.current_action.configure(text_color="gray")

    def update_progress(self, type, val):
        if type == "step":
            self.stat_step.configure(text=f"STEP: {val}/30")

    def update_metric(self, type, val):
        if type == "Reward":
            color = "green" if val > 0 else "red"
            self.stat_reward.configure(text=f"REWARD: {val}", text_color=color)

    def refresh_intel(self):
        if not self.blackboard: return
        
        state = self.blackboard.state
        txt = "[Blackboard] INTELLIGENCE UPDATE:\n"
        
        open_ports = list(state['ports'].keys())
        txt += f"   :: Open Ports: {open_ports}\n"
        
        os_disp = state['os_info']
        if os_disp == "Unknown": os_disp = "Unknown (Cloud/Firewall Protected)"
        txt += f"   :: OS Detected: {os_disp}\n"
        
        mac_disp = state['mac_address']
        if mac_disp == "Unknown": mac_disp = "Unknown (Remote Target - Layer 2 Hidden)"
        txt += f"   :: MAC Address: {mac_disp}\n"
        txt += "\n"
        
        txt += "-"*30 + "\n"
        txt += "DETAILED PORT ANALYSIS:\n"
        txt += "-"*30 + "\n"
        
        if not state['ports']:
            txt += "No open ports found yet.\n"
        
        for p, s in state['ports'].items():
            txt += f"-> Port {p}: {s}\n"
            for v in state['network_vulns']:
                if f"Port {p}:" in v:
                    detail = v.replace(f"Port {p}:", "").strip()
                    txt += f"   [!] {detail}\n"
        
        txt += "\n"
        txt += "-"*30 + "\n"
        txt += "WEB VULNERABILITIES:\n"
        txt += "-"*30 + "\n"
        
        if not state['vulnerabilities']:
            txt += "No web vulnerabilities confirmed.\n"
        else:
            for v in state['vulnerabilities']:
                txt += f"[CRITICAL] {v}\n"

        if state['flag_captured']:
             txt += "\n"
             txt += "*"*30 + "\n"
             txt += "FLAGS CAPTURED:\n"
             txt += "*"*30 + "\n"
             for entry in state['activity_log']:
                 if "FLAG" in str(entry['details']):
                     txt += f">> {entry['details']}\n"
        
        self.intel_text.configure(state="normal")
        self.intel_text.delete("0.0", END)
        self.intel_text.insert("0.0", txt)
        self.intel_text.configure(state="disabled")

if __name__ == "__main__":
    app = RaiderDashboard()
    app.mainloop()