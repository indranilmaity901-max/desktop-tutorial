import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import secrets
import statistics
import time

import httpx
import psycopg
from psycopg.rows import dict_row
import websockets


def hash_password(password: str) -> str:
    iterations = 260000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def seed(database_url: str, admin_password: str, manager_password: str, agent_count: int):
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            for role in ("ADMIN", "MANAGER", "AGENT"):
                cursor.execute("INSERT INTO roles (role_name) VALUES (%s) ON CONFLICT (role_name) DO NOTHING", (role,))
            cursor.execute("SELECT role_id FROM roles WHERE role_name = 'ADMIN'")
            admin_role = cursor.fetchone()["role_id"]
            cursor.execute("SELECT role_id FROM roles WHERE role_name = 'MANAGER'")
            manager_role = cursor.fetchone()["role_id"]
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role_id, active)
                VALUES ('load-admin', %s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role_id = EXCLUDED.role_id, active = TRUE
                RETURNING user_id
                """,
                (hash_password(admin_password), admin_role),
            )
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role_id, active)
                VALUES ('load-manager', %s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role_id = EXCLUDED.role_id, active = TRUE
                RETURNING user_id
                """,
                (hash_password(manager_password), manager_role),
            )
            manager_id = str(cursor.fetchone()["user_id"])
            for number in range(agent_count):
                employee_id = f"LOAD-{number:03d}"
                cursor.execute(
                    """
                    INSERT INTO employees (employee_id, employee_name, department, manager_id, status)
                    VALUES (%s, %s, 'Load Test', %s, 'ACTIVE')
                    ON CONFLICT (employee_id) DO UPDATE SET manager_id = EXCLUDED.manager_id, status = 'ACTIVE'
                    """,
                    (employee_id, f"Load Agent {number:03d}", manager_id),
                )
    return [f"LOAD-{number:03d}" for number in range(agent_count)]


async def login(client: httpx.AsyncClient, username: str, password: str, role: str) -> str:
    response = await client.post(
        "/api/v2/auth/login",
        json={"username": username, "password": password, "role": role},
    )
    response.raise_for_status()
    return response.json()["data"]["access_token"]


async def websocket_client(url: str, token: str, stop: asyncio.Event, deliveries: list):
    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    async with websockets.connect(f"{ws_url}/api/v2/live?token={token}") as websocket:
        while not stop.is_set():
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1)
                payload = json.loads(message)
                if payload.get("type") in {"workstation_event", "agent_status", "productivity"}:
                    deliveries.append(time.perf_counter())
            except asyncio.TimeoutError:
                continue


async def send_event(client: httpx.AsyncClient, token: str, employee_id: str, event_type: str, latencies: list, failures: list):
    start = time.perf_counter()
    response = await client.post(
        "/api/v2/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_id": employee_id,
            "event_type": event_type,
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "load_test",
        },
    )
    elapsed = (time.perf_counter() - start) * 1000
    latencies.append(elapsed)
    if response.status_code >= 400:
        failures.append({"employee_id": employee_id, "event_type": event_type, "status": response.status_code, "body": response.text})


async def run(args):
    employee_ids = seed(args.database_url, args.admin_password, args.manager_password, args.agents)
    async with httpx.AsyncClient(base_url=args.api_url, timeout=20) as client:
        admin_token = await login(client, "load-admin", args.admin_password, "ADMIN")
        manager_token = await login(client, "load-manager", args.manager_password, "MANAGER")
        stop = asyncio.Event()
        deliveries = []
        sockets = [
            asyncio.create_task(websocket_client(args.api_url, manager_token, stop, deliveries))
            for _ in range(args.manager_clients)
        ]
        await asyncio.sleep(1)
        latencies = []
        failures = []
        tasks = []
        for employee_id in employee_ids:
            tasks.append(send_event(client, admin_token, employee_id, "SHIFT_START", latencies, failures))
            tasks.append(send_event(client, admin_token, employee_id, "HEARTBEAT", latencies, failures))
            tasks.append(send_event(client, admin_token, employee_id, "LOCK", latencies, failures))
            tasks.append(send_event(client, admin_token, employee_id, "UNLOCK", latencies, failures))
            tasks.append(send_event(client, admin_token, employee_id, "HEARTBEAT", latencies, failures))
        await asyncio.gather(*tasks)
        await asyncio.sleep(args.delivery_wait)
        stop.set()
        await asyncio.gather(*sockets, return_exceptions=True)
    successful = len(latencies) - len(failures)
    report = {
        "agents": args.agents,
        "manager_websocket_clients": args.manager_clients,
        "events_attempted": len(latencies),
        "db_write_success": successful,
        "db_write_failures": len(failures),
        "websocket_messages_received": len(deliveries),
        "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0,
        "latency_ms_p95": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else 0,
        "failures": failures[:10],
    }
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="WPACS V2 load validation")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--manager-password", required=True)
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--manager-clients", type=int, default=20)
    parser.add_argument("--delivery-wait", type=float, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
