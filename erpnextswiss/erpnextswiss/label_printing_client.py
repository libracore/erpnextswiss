#!/usr/bin/env python3
import requests
import fcntl
import json
import os, sys, time, socket

API_KEY = "8d2d72248e2a39f"
API_SECRET = "6cbf78131f171a0"
PRINTER_GROUP = "Mygrp"

BASE_URL = "http://localhost:8000"
API_URL = BASE_URL + "/api/method/erpnextswiss.erpnextswiss.print_queue.get_group_jobs"
MARK_DONE_URL = BASE_URL + "/api/method/erpnextswiss.erpnextswiss.print_queue.set_job_status"

PRINT_JOBS_LIMIT = 10
LOCKFILE = "/tmp/print_worker.lock"
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": "token {API_KEY}:{API_SECRET}".format(API_KEY=API_KEY, API_SECRET=API_SECRET),
    "Content-Type": "application/json"
})


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
    params = {"group_name": PRINTER_GROUP, "limit": PRINT_JOBS_LIMIT}
    # Using POST so body can be JSON; Frappe accepts form too.
    r = SESSION.post(API_URL, json=params, timeout=70)  # a little > LONG_POLL_SECONDS
    r.raise_for_status()
    return r.json().get("message")  # frappe returns wrapped in "message"

def process_job(job):
    try:
        job_bytes = base64.b64decode(job['data_base64'])
        send_via_socket(job['printer_hostname'], job['printer_port'], job_bytes)
        mark_done(job["name"], "Printed")
    except Exception as e:
        mark_done(job["name"], "Failed", e)

def mark_done(job_name, status, message):
    payload = {"job_name": job_name, "status": status, "message": message}
    try:
        r = SESSION.post(MARK_DONE_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        # log locally; will be retried by admin or separate process
        print("Mark done failed:", e)

def main():
    lock = obtain_lock()
    if not lock:
        # another instance running
        return
    try:
        resp = fetch_jobs()
        if not resp:
            return
        # API returns {"jobs": [...], "timed_out": bool}
        jobs = resp.get("jobs", [])
        timed_out = resp.get("timed_out", False)
        if timed_out and not jobs:
            # long poll ended with no jobs — per requirement, call again immediately once
            resp2 = fetch_jobs()
            jobs = (resp2 or {}).get("jobs", [])
        for job in jobs:
            process_job(job)
    finally:
        release_lock(lock)

def send_via_socket(host, port, data):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.connect((host, port))
    soc.sendall(data)
    soc.close()

if __name__ == "__main__":
    main()
