import subprocess
import os
import sys
import threading
import time

def run_command(command, cwd, prefix, env=None):
    print(f"[{prefix}] Starting: {command}")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True,
        env=env
    )
    
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"[{prefix}] {line.strip()}", flush=True)
            
    process.wait()
    return process.returncode

def setup_dependencies(backend_dir, frontend_dir):
    print("[SYSTEM] Checking dependencies...")
    
    
    # Frontend dependencies
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("[FRONTEND] Installing Node dependencies... (this might take a minute)")
        subprocess.run("npm install", cwd=frontend_dir, shell=True)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    setup_dependencies(backend_dir, frontend_dir)
    
    # Setup custom environment for backend to run completely local without docker
    backend_env = os.environ.copy()
    backend_env["DATABASE_URL"] = "sqlite:///./local_test.db"
    backend_env["MQTT_BROKER"] = "test.mosquitto.org"
    
    print("\n" + "="*50)
    print("Starting Local Emergency Warning System")
    print("="*50 + "\n")
    
    # Start Backend
    backend_cmd = f'"{sys.executable}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
    backend_thread = threading.Thread(
        target=run_command, 
        args=(backend_cmd, backend_dir, "BACKEND", backend_env)
    )
    backend_thread.daemon = True
    backend_thread.start()
    
    time.sleep(2)
    
    # Start Frontend
    frontend_cmd = "npm start"
    frontend_thread = threading.Thread(
        target=run_command, 
        args=(frontend_cmd, frontend_dir, "FRONTEND")
    )
    frontend_thread.daemon = True
    frontend_thread.start()
    
    try:
        print("\n[SYSTEM] Services started. Press Ctrl+C to stop.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down services...")
        sys.exit(0)

if __name__ == "__main__":
    main()