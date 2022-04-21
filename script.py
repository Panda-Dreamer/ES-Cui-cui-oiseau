from subprocess import run
from time import sleep


restart_timer = 2
def start_script():
    try:
        # Make sure 'python' command is available
        print("Launching server...")
        run("python3 server.py --language fr", check=True) 
    except Exception as e: 
        # Script crashed, lets restart it!
        print(e)
        handle_crash()

def handle_crash():
    sleep(restart_timer)  # Restarts the script after 2 seconds
    start_script()

start_script()