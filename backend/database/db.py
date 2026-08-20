import sqlite3
import os
from typing import Dict, Any, List, Optional
import uuid
import datetime

DB_PATH = "lambdax.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.execute('pragma journal_mode=wal')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Functions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS functions (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        image TEXT NOT NULL,
        memory_mb INTEGER,
        sla_ms INTEGER,
        max_containers INTEGER,
        max_warm_containers INTEGER,
        idle_timeout_seconds INTEGER,
        scheduling_policy TEXT DEFAULT 'reactive',
        min_containers INTEGER DEFAULT 0,
        queue_threshold INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    # Containers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS containers (
        id TEXT PRIMARY KEY,
        container_id TEXT NOT NULL,
        function_id TEXT NOT NULL,
        state TEXT NOT NULL,
        created_at TEXT,
        started_at TEXT,
        last_used_at TEXT,
        last_state_change_at TEXT,
        FOREIGN KEY (function_id) REFERENCES functions (id)
    )
    """)

    # Invocations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invocations (
        id TEXT PRIMARY KEY,
        function_id TEXT NOT NULL,
        container_id TEXT,
        timestamp TEXT,
        queue_entered_at TEXT,
        queue_exit_at TEXT,
        queue_time_ms REAL,
        cold_start BOOLEAN,
        startup_time_ms REAL,
        execution_time_ms REAL,
        total_latency_ms REAL,
        sla_ms INTEGER,
        sla_met BOOLEAN,
        status TEXT,
        scheduling_policy TEXT,
        FOREIGN KEY (function_id) REFERENCES functions (id)
    )
    """)

    # Scheduler Decisions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduler_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        function_id TEXT NOT NULL,
        timestamp REAL,
        action TEXT,
        target_containers INTEGER,
        reason TEXT,
        confidence REAL,
        predicted_demand REAL,
        sla_margin_ms REAL,
        expected_wait_ms REAL,
        estimated_cost REAL,
        FOREIGN KEY (function_id) REFERENCES functions (id)
    )
    """)

    # Clear containers on startup (to simulate fresh state if Docker is clean)
    # Actually, we should probably just sync it, but for Phase 2 we can start fresh.
    cursor.execute("DELETE FROM containers")
    
    conn.commit()
    conn.close()

def execute_write(query: str, params: tuple = ()):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def execute_read(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def execute_read_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    rows = execute_read(query, params)
    return rows[0] if rows else None
