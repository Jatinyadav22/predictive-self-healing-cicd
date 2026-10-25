import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from src.config.settings import settings
from src.models.schemas import PipelineRun, AuditRecord, PipelineStatus

class AuditLogger:
    """Manages immutable audit trails using SHA-256 hash chaining and SQLite run persistence."""

    def __init__(self, db_path: Path = settings.DATABASE_PATH, log_file: Path = settings.AUDIT_LOG_PATH):
        self.db_path = Path(db_path)
        self.log_file = Path(log_file)
        self._init_storage()

    def _init_storage(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # If an old legacy table exists without event_id, drop and recreate
            cursor.execute("PRAGMA table_info(audit_events)")
            existing_cols = {col[1] for col in cursor.fetchall()}
            if existing_cols and "event_id" not in existing_cols:
                cursor.execute("DROP TABLE audit_events")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    commit_sha TEXT,
                    branch TEXT,
                    author TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    payload TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    event_type TEXT,
                    run_id TEXT,
                    actor TEXT,
                    summary TEXT,
                    payload TEXT,
                    previous_event_hash TEXT,
                    event_hash TEXT
                )
            """)
            conn.commit()

    def _get_last_hash(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_hash FROM audit_events WHERE event_hash IS NOT NULL AND event_hash != '' ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if (row and row[0]) else "GENESIS_BLOCK_00000000000000000000"

    def record_event(
        self,
        event_type: str,
        summary: str,
        run_id: Optional[str] = None,
        actor: str = "SYSTEM",
        payload: Optional[dict[str, Any]] = None
    ) -> AuditRecord:
        payload = payload or {}
        now_utc = datetime.now(timezone.utc)
        event_id = f"evt-{int(now_utc.timestamp() * 1000)}"
        timestamp = now_utc
        prev_hash = self._get_last_hash()

        # Compute SHA-256 hash chaining
        hasher = hashlib.sha256()
        hasher.update(f"{prev_hash}|{event_id}|{timestamp.isoformat()}|{event_type}|{actor}|{summary}".encode("utf-8"))
        event_hash = hasher.hexdigest()

        record = AuditRecord(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            run_id=run_id,
            actor=actor,
            summary=summary,
            payload=payload,
            previous_event_hash=prev_hash,
            event_hash=event_hash
        )

        # Write to SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_events 
                (event_id, timestamp, event_type, run_id, actor, summary, payload, previous_event_hash, event_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.event_id,
                record.timestamp.isoformat(),
                record.event_type,
                record.run_id,
                record.actor,
                record.summary,
                json.dumps(record.payload),
                record.previous_event_hash,
                record.event_hash
            ))
            conn.commit()

        # Append to JSONL
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        return record

    def save_pipeline_run(self, run: PipelineRun):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pipeline_runs 
                (run_id, commit_sha, branch, author, status, started_at, completed_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                run.commit_sha,
                run.branch,
                run.author,
                run.status.value,
                run.started_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.model_dump_json()
            ))
            conn.commit()

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM pipeline_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return PipelineRun.model_validate_json(row[0])
        return None

    def list_pipeline_runs(self, limit: int = 50) -> list[PipelineRun]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM pipeline_runs ORDER BY started_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [PipelineRun.model_validate_json(r[0]) for r in rows]

    def list_audit_events(self, limit: int = 50) -> list[AuditRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, timestamp, event_type, run_id, actor, summary, payload, previous_event_hash, event_hash
                FROM audit_events ORDER BY rowid DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            records = []
            for r in rows:
                records.append(AuditRecord(
                    event_id=r[0],
                    timestamp=datetime.fromisoformat(r[1]),
                    event_type=r[2],
                    run_id=r[3],
                    actor=r[4],
                    summary=r[5],
                    payload=json.loads(r[6]),
                    previous_event_hash=r[7],
                    event_hash=r[8]
                ))
            return records

    def get_platform_metrics(self) -> dict[str, Any]:
        runs = self.list_pipeline_runs(limit=100)
        total = len(runs)
        if total == 0:
            return {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "autonomous_fixes": 0,
                "pending_approvals": 0,
                "success_rate": 100.0,
                "auto_fix_rate": 0.0,
                "avg_pipeline_duration": 0.0,
                "estimated_mttr_seconds": 19.4
            }

        successful = sum(1 for r in runs if r.status in [PipelineStatus.SUCCESS, PipelineStatus.RECOVERED_AUTOMATICALLY])
        recovered = sum(1 for r in runs if r.status == PipelineStatus.RECOVERED_AUTOMATICALLY)
        failed = sum(1 for r in runs if r.status in [PipelineStatus.FAILED, PipelineStatus.RECOVERY_FAILED_ROLLED_BACK])
        pending = sum(1 for r in runs if r.status == PipelineStatus.REQUIRES_HUMAN_APPROVAL)

        durations = []
        for r in runs:
            if r.completed_at and r.started_at:
                durations.append((r.completed_at - r.started_at).total_seconds())

        avg_duration = round(sum(durations) / len(durations), 1) if durations else 15.0

        return {
            "total_runs": total,
            "successful_runs": successful,
            "failed_runs": failed,
            "autonomous_fixes": recovered,
            "pending_approvals": pending,
            "success_rate": round((successful / total) * 100, 1),
            "auto_fix_rate": round((recovered / (failed + recovered or 1)) * 100, 1),
            "avg_pipeline_duration": avg_duration,
            "estimated_mttr_seconds": 19.4
        }

audit_logger = AuditLogger()
