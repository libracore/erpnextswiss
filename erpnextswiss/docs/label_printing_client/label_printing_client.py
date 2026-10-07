#!/usr/bin/env python3
import requests
import fcntl
import json, base64
import os, sys, time, socket
import traceback
import signal, threading, random

API_KEY = "8d2d72248e2a39f"
API_SECRET = "6cbf78131f171a0"
PRINTER_GROUP = "Mygrp"

BASE_URL = "http://localhost:8000"
API_URL = BASE_URL + "/api/method/erpnextswiss.erpnextswiss.print_queue.get_group_jobs"
MARK_DONE_URL = BASE_URL + "/api/method/erpnextswiss.erpnextswiss.print_queue.set_job_status"

PRINT_JOBS_LIMIT = 10
LOCKFILE = "/tmp/print_worker.lock"
SOCKET_TIMEOUT = 10.0
MIN_BACKOFF = 2.0         # Backoff time on error (sec)
MAX_BACKOFF = 60.0
_shutdown_event = threading.Event()
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": "token {API_KEY}:{API_SECRET}".format(API_KEY=API_KEY, API_SECRET=API_SECRET),
    "Content-Type": "application/json"
})

def _handle_signal(signum, frame):
    _shutdown_event.set()

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

def obtain_lock():
    fd = open(LOCKFILE, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except IOError:
        fd.close()
        return None

def release_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()

def fetch_jobs():
    def trace_function(frame, event, arg):
        if _shutdown_event.is_set():
            print(" --- Aborted --- ")
            sys.exit(1)
        return trace_function

    sys.settrace(trace_function)
    try:
        params = {"group_name": PRINTER_GROUP, "limit": PRINT_JOBS_LIMIT}
        # Using POST so body can be JSON; Frappe accepts form too.
        r = SESSION.post(API_URL, json=params, timeout=70)  # a little > LONG_POLL_SECONDS
        r.raise_for_status()
        return r.json().get("message")  # frappe returns wrapped in "message"
    finally:
        sys.settrace(None)

def process_job(job):
    try:
        job_bytes = base64.b64decode(job['data_base64'])
        send_via_socket(job['printer_hostname'], job['printer_port'], job_bytes)
        mark_done(job["name"], "Printed")
    except Exception as e:
        mark_done(job.get("name", "<unknown>"), "Failed", traceback.format_exc())
        print("Job processing failed:")
        traceback.print_exc()

def mark_done(job_name, status, message=""):
    payload = {"job_name": job_name, "status": status, "message": message}
    try:
        r = SESSION.post(MARK_DONE_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        # log locally; will be retried by admin or separate process
        print("Mark done failed:")
        traceback.print_exc()

def main():
    print("Obtaining lock...")
    lock = obtain_lock()
    if not lock:
        print("Lock failed, another instance may be running.")
        return

    print("Entering loop.")
    backoff = MIN_BACKOFF
    try:
        while True:
            if _shutdown_event.is_set():
                break

            print("Requesting print jobs from server...")
            try:
                resp = fetch_jobs()
            except Exception as e:
                print("fetch_jobs failed:", e)
                sleep_for = backoff * (0.8 + 0.4 * random.random())  # jitter
                time.sleep(sleep_for)
                backoff = min(MAX_BACKOFF, backoff * 2)
                continue

            # Reset backoff on success
            backoff = MIN_BACKOFF

            # API returns {"jobs": [...], "timed_out": bool}
            jobs = resp.get("jobs", [])
            timed_out = resp.get("timed_out", False)

            if jobs:
                print("Processing print jobs...")
                for job in jobs:
                    if _shutdown_event.is_set():
                        break
                    process_job(job)

            if _shutdown_event.is_set():
                break

            if timed_out:
                print("Long polling timeout, sending next request directly.")
            else:
                print("Random sleep...")
                # small randomized sleep to reduce sync storms
                time.sleep(0.1 + random.random() * 0.4)

    finally:
        release_lock(lock)

def send_via_socket(host, port, data):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = int(port) or 9100
    soc.settimeout(SOCKET_TIMEOUT)
    try:
        soc.connect((host, port))
        soc.sendall(data)
        try:
            soc.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
    finally:
        soc.close()

if __name__ == "__main__":
    main()
