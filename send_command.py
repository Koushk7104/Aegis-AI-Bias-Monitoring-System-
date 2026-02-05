import sys
import requests

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:8000/add_command"

def send_command(command):
    """Sends a single command to the running AI server."""
    if command not in ['F', 'B']:
        print("Error: Invalid command. Please use 'F' or 'B'.")
        print("Example: python send_command.py F")
        return

    try:
        print(f"Sending command '{command}' to server...")
        payload = {"command": command}
        response = requests.post(SERVER_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"SUCCESS: Server confirmed command '{command}' was processed.")
    except requests.exceptions.RequestException as e:
        print("\n--- CONNECTION ERROR ---")
        print("Could not connect to the AI server.")
        print("Please ensure 'run_ai_server.py' is running and accessible.")
        print(f"Details: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_command.py <command>")
        print("Commands: 'F' (for Fair) or 'B' (for Biased)")
    else:
        command_to_send = sys.argv[1].upper()
        send_command(command_to_send)

