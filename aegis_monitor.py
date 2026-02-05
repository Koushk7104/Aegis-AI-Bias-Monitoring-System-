import time
from collections import deque
from datetime import datetime

import pandas as pd
import requests
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# --- CONFIGURATION ---
WINDOW_SIZE = 50
BIAS_THRESHOLD = 0.8
POLL_INTERVAL = 1
SERVER_URL = "http://127.0.0.1:8000/get_decisions"

console = Console()

def make_layout() -> Layout:
    """Defines the aggressive, multi-panel layout."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(size=5, name="footer"),
    )
    layout["main"].split_row(Layout(name="metrics", ratio=2), Layout(name="status", ratio=1))
    return layout

def generate_header() -> Panel:
    """Generates an aggressive ASCII art header."""
    header_text = Text.from_markup(r"""
█████╗ ███████╗ ██████╗ ██╗ ██████╗       / \----------------, 
╚════╝ ██╔════╝██╔════╝ ██║██╔════╝      / / \                \
     ███████╗██║  ███╗██║██║  ╔═══╗     / /   \      MONITOR   \
     ╚═══██║██║   ██║██║██║   ██║    / /     \                /
     ███████║╚██████╔╝██║╚██████╔╝   '         \______________/
     ╚══════╝ ╚═════╝ ╚═╝ ╚═════╝
    """, justify="center", style="white")
    return Panel(header_text, box=box.HEAVY, border_style="bright_black")

def generate_metrics_table(parity, status) -> Panel:
    """Generates a stark metrics table."""
    table = Table(box=None, expand=True)
    table.add_column("METRIC", style="bright_black", no_wrap=True, ratio=2)
    table.add_column("VALUE", style="white", ratio=1)
    table.add_column("STATUS", justify="right", style="bold", ratio=2)

    status_style = "green" if status == "SYSTEM NOMINAL" else "bold red"
    table.add_row("Demographic Parity", f"{parity:.2f}", Text(status, style=status_style))
    
    title = "[white]>> BIAS ANALYSIS <<[/white]"
    border_color = "bright_black"
    if status != "SYSTEM NOMINAL":
        title = "[bold red]>> CRITICAL BIAS ALERT <<[/bold red]"
        border_color = "bold red"

    return Panel(table, title=title, box=box.HEAVY, border_style=border_color)

def generate_threat_panel(parity, is_connected) -> Panel:
    """Generates a threat level indicator."""
    threat_text = Text("CONNECTION LOST", style="bold red", justify="center")
    if is_connected:
        if parity < BIAS_THRESHOLD:
            level = "CRITICAL"
            color = "red"
            bar_fill = 5
        elif parity < 0.9:
            level = "ELEVATED"
            color = "yellow"
            bar_fill = 3
        else:
            level = "NOMINAL"
            color = "green"
            bar_fill = 1
        
        bar = "█" * bar_fill + "─" * (5 - bar_fill)
        threat_text = Text.assemble(
            (f"THREAT LEVEL: {level}\n", f"bold {color}"),
            (f"[{bar}]", color)
        , justify="center")

    return Panel(threat_text, title="[white]> THREAT LEVEL <[/white]", box=box.HEAVY, border_style="bright_black")

def generate_log_panel(log_messages: deque) -> Panel:
    """Generates the log panel."""
    log_renderable = Text("\n".join(log_messages))
    return Panel(log_renderable, title="[white]>> DATASTREAM LOG <<[/white]", box=box.HEAVY, border_style="bright_black")

def main():
    decision_window = deque(maxlen=WINDOW_SIZE)
    log_messages = deque(maxlen=3)
    layout = make_layout()
    is_connected = False

    with Live(layout, screen=True, redirect_stderr=False, refresh_per_second=4) as live:
        try:
            log_messages.append(f">> Connecting to C2 Server: {SERVER_URL}...")
            
            while True:
                new_data_df = None
                try:
                    response = requests.get(SERVER_URL, timeout=1)
                    response.raise_for_status()
                    decisions = response.json()
                    if decisions:
                        new_data_df = pd.DataFrame(decisions)
                    is_connected = True
                except requests.exceptions.RequestException:
                    is_connected = False
                    log_messages.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] CONNECTION FAILED. RETRYING...")


                if new_data_df is not None:
                    for _, row in new_data_df.iterrows():
                        decision_window.append(row)
                        approved_text = "Approved" if row['decision'] == 1 else "Rejected"
                        log_messages.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] RECV: {approved_text} | GRP: {row['group']}")

                df_window = pd.DataFrame(list(decision_window))
                parity, _ = calculate_demographic_parity(df_window)
                status = "CRITICAL ALERT" if parity < BIAS_THRESHOLD and is_connected else "SYSTEM NOMINAL"
                
                layout["header"].update(generate_header())
                layout["metrics"].update(generate_metrics_table(parity, status))
                layout["status"].update(generate_threat_panel(parity, is_connected))
                layout["footer"].update(generate_log_panel(log_messages))
                live.refresh()
                
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            console.print(">> MONITOR SHUTDOWN SIGNALLED.", style="bold yellow")
        except Exception as e:
            console.print(f">> FATAL SYSTEM ERROR: {e}", style="bold red")

def calculate_demographic_parity(df: pd.DataFrame):
    if df.empty or len(df) < 10: return 1.0, ""
    group_outcomes = df.groupby('group')['decision'].agg(['mean', 'count']).rename(columns={'mean': 'approval_rate'})
    if len(group_outcomes) < 2: return 1.0, ""
    rate_a = group_outcomes.loc['Group_A', 'approval_rate'] if 'Group_A' in group_outcomes.index else 0
    rate_b = group_outcomes.loc['Group_B', 'approval_rate'] if 'Group_B' in group_outcomes.index else 0
    if max(rate_a, rate_b) == 0: return 1.0, ""
    parity = min(rate_a, rate_b) / max(rate_a, rate_b) if max(rate_a, rate_b) > 0 else 1.0
    return parity, group_outcomes.to_string()

if __name__ == "__main__":
    main()

