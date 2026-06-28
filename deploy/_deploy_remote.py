#!/usr/bin/env python3
"""Remote deployment helper - handles process start/stop on remote server."""
import subprocess
import sys
import time
import os

REMOTE_PATH = os.environ.get('REMOTE_PATH', '/opt/app')

def run(cmd, timeout=15):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr

def stop_service(pattern):
    """Stop process matching pattern."""
    print(f"[STOP] Killing {pattern}...")
    run(f"pkill -f '{pattern}' || true")
    time.sleep(2)
    run(f"pkill -9 -f '{pattern}' || true")
    time.sleep(1)
    print(f"[STOP] Done")

def start_service(script_name, log_file):
    """Start service in background using start_new_session (detaches from SSH)."""
    cmd = "cd '" + REMOTE_PATH + "' && python3 " + script_name
    print(f"[START] {script_name} ...")
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=open(log_file, 'a'),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    print(f"[START] {script_name} launched (pid={proc.pid})")
    return True

def health_check(port, path):
    """Check health endpoint."""
    time.sleep(3)
    rc, out, err = run(f"curl -s --max-time 5 http://localhost:{port}{path}")
    print(f"[HEALTH] {out.strip() if out else 'no response'}")

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'deploy'

    if action == 'stop':
        stop_service('backend/main.py')
        stop_service('backend/run_scheduler.py')
        print("[DONE] All stopped")
    elif action == 'deploy':
        # Stop old services
        stop_service('backend/main.py')
        stop_service('backend/run_scheduler.py')

        # Start main.py
        start_service('backend/main.py', '/var/log/news_collector.log')

        # Start scheduler
        start_service('backend/run_scheduler.py', '/var/log/news_scheduler.log')

        # Health check
        health_check(31234, '/api/health')

        print("[DONE] Deployment complete")
    elif action == 'start-services':
        start_service('backend/main.py', '/var/log/news_collector.log')
        start_service('backend/run_scheduler.py', '/var/log/news_scheduler.log')
        health_check(31234, '/api/health')
        print("[DONE] Services started")
    elif action == 'stop-services':
        stop_service('backend/main.py')
        stop_service('backend/run_scheduler.py')
        print("[DONE] Services stopped")

if __name__ == '__main__':
    main()