import time
import random
from datetime import datetime

LOG_FILE = "server_app.log"

# Different "levels" of logs to simulate a real system
log_templates = [
    ("INFO", "Connection established from 192.168.1.{ip}"),
    ("INFO", "User {user} authenticated successfully."),
    ("WARN", "High memory usage detected: {mem}%"),
    ("ERROR", "Database connection timeout. Retrying..."),
    ("ERROR", "Payment gateway 502 Bad Gateway."),
    ("CRITICAL", "SERVICE CRASH: NullPointerException in module auth.py line {line}"),
]

users = ["alice", "bob", "admin", "system"]

print(f"--- Starting Log Generator. Writing to {LOG_FILE} ---")

try:
    while True:
        # Pick a random log event
        level, msg = random.choice(log_templates)

        # Fill in the placeholders with random data
        log_message = msg.format(
            ip=random.randint(2, 255),
            user=random.choice(users),
            mem=random.randint(80, 99),
            line=random.randint(10, 500),
        )

        # Create timestamp
        timestamp = datetime.now().strftime("%b %d %H:%M:%S")

        # Format: Dec 10 14:00:01 HOSTNAME LEVEL: Message
        full_log = f"{timestamp} my-server {level}: {log_message}\n"

        # Append to file
        with open(LOG_FILE, "a") as f:
            f.write(full_log)

        print(f"Wrote: {full_log.strip()}")

        # Wait a bit (simulate random traffic)
        time.sleep(random.uniform(1, 4))

except KeyboardInterrupt:
    print("\nStopping Log Generator.")
