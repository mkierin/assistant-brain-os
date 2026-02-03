import os
import subprocess
import time
import sys
import redis

def check_redis():
    print("Checking for Redis server...")
    try:
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.ping()
        print("Found existing Redis server.")
        return True
    except:
        return False

def run_process(name, cmd):
    print(f"Starting {name}...")
    return subprocess.Popen(cmd, shell=True)

def main():
    has_redis = check_redis()
    if not has_redis:
        print("WARNING: Redis not found. Please install Redis for Windows.")
        print("Continuing with process management...")

    processes = []
    try:
        p_main = run_process("Main (Telegram)", [sys.executable, "main.py"])
        processes.append(p_main)
        p_worker = run_process("Worker", [sys.executable, "worker.py"])
        processes.append(p_worker)
        
        print("\nSystems running via manage.py. Press Ctrl+C to stop.")
        while True:
            time.sleep(2)
            if p_main.poll() is not None:
                p_main = run_process("Main (Telegram)", [sys.executable, "main.py"])
            if p_worker.poll() is not None:
                p_worker = run_process("Worker", [sys.executable, "worker.py"])
    except KeyboardInterrupt:
        for p in processes: p.terminate()

if __name__ == "__main__":
    main()
