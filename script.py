from subprocess import run
from time import sleep
import os

restart_timer = 2
def start_script():
    try:
        # Make sure 'python' command is available
        print("Launching server...")
        os.system("python3 server.py --locale fr") 
    except Exception as e: 
        # Script crashed, lets restart it!
        print(e)
        handle_crash()

def handle_crash():
    sleep(restart_timer)  # Restarts the script after 2 seconds
    start_script()

start_script()