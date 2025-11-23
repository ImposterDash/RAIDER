# RAIDER
### **R**einforcement **A**gents for **I**ntelligent **D**iscovery and **E**xploit **R**esearch

**RAIDER** is an autonomous AI Red Teaming system that combines **Reinforcement Learning (RL)** for strategic decision-making with **Large Language Models (LLM)** for tactical execution.

Instead of hard-coded scripts, RAIDER uses a Q-Learning "Commander" to decide *when* to scan and *when* to attack, while an LLM-driven "Exploit Agent" analyzes web pages in real-time to generate context-aware SQL injection payloads.

---

## Architecture

RAIDER operates using a **Blackboard Architecture** where specialized agents collaborate:

1.  **The Commander (RL Core)** 
    * **Logic:** Q-Learning (Reinforcement Learning).
    * **Role:** Learns the optimal "Kill Chain" order. It is rewarded for capturing flags and punished for premature attacks or stagnation.
2.  **The Discovery Agent (Recon)**
    * **Tools:** Nmap (Port Scanner).
    * **Role:** Identifies open ports (HTTP, SSH, etc.) and surfaces the attack landscape to the Blackboard.
3.  **The Intelligent Agent (Exploit)**
    * **Tools:** Google Gemini + Selenium.
    * **Role:** Parses HTML structures, identifies login forms, and generates bespoke SQL injection payloads based on previous failure logs.

---

## Installation

### 1. Critical Prerequisite: Nmap Binary
**You must install the Nmap application on your system.**
The Python library (`python-nmap`) is only a wrapper.

* **Windows:**
    * Download the setup `.exe` from the official website: [https://nmap.org/download.html](https://nmap.org/download.html)
* **Linux (Debian/Ubuntu):**
    ```bash
    sudo apt-get install nmap
    ```
* **macOS:**
    ```bash
    brew install nmap
    ```

### 2. Project Setup

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/ayushgayakwad/RAIDER.git](https://github.com/ayushgayakwad/RAIDER.git)
    cd RAIDER
    ```

2.  **Install Python Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**
    Create a ```.env``` file in the root directory and add your Gemini API key:
    ```env
    GEMINI_API_KEY=your_actual_api_key_here
    ```

---

## Usage

### 1. Quick Start (Mock Mode)
To see RAIDER in action without an external target, simply run the main script and press **ENTER** when prompted for a URL. This launches a local vulnerable Flask server (The "SecureCorp Bank").

```bash
python main.py
Enter Target URL (or press Enter for Localhost): # Just press Enter to activate the Mock Mode
```

* **Target**: http://127.0.0.1:5000
* **Goal**: Bypass the login screen and capture the flag ```FLAG{MULTI_AGENT_DOMINATION}```.

### 2. Live Targeting
You can point RAIDER at a specific URL or IP address (ensure you have permission!).

```bash
python main.py
Enter Target URL (or press Enter for Localhost): # Enter the URL of the target website
```

* A list of few sample live target websites is available in ```sample_live_targets.md```.

