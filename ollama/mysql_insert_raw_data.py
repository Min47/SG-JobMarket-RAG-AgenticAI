import json
import mysql.connector
from datetime import datetime, timezone
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'job_data',
    'charset': 'utf8mb4'
}

def stage1_load_raw_mysql(
    local_file_path: Path,
    source: str, # Fallback source name if not present in JSONL
    scrape_timestamp: datetime, # Fallback scrape timestamp if not present in JSONL
    db_config: dict
) -> dict:
    """Stage 1: Load JSONL directly into local MySQL raw_jobs table."""
    stage_start = datetime.now(timezone.utc)
    
    total_lines = 0
    valid_rows = []
    invalid_rows = 0

    # Step 1: Parse JSONL line-by-line
    try:
        with open(local_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                total_lines += 1
                line = line.strip()
                if not line: continue
                
                try:
                    data = json.loads(line)
                    job_id = data.get("job_id")
                    payload = data.get("payload")

                    if not job_id or not isinstance(payload, dict):
                        invalid_rows += 1
                        continue

                    # Prep data for MySQL batch insert
                    # We use the raw payload dictionary directly
                    valid_rows.append((
                        str(job_id),
                        data.get("source", source),
                        data.get("scrape_timestamp", scrape_timestamp.isoformat()),
                        json.dumps(payload) # MySQL JSON columns take strings
                    ))

                except (json.JSONDecodeError, Exception):
                    invalid_rows += 1
                    continue
    except Exception as e:
        print(f"File Error: {e}")
        raise

    # Step 2: Batch Insert into MySQL
    streamed_rows = 0
    if valid_rows:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            sql = """
                INSERT INTO raw_jobs (job_id, source, scrape_timestamp, payload)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    scrape_timestamp = VALUES(scrape_timestamp),
                    payload = VALUES(payload)
            """
            
            # Batch size of 500 for efficiency
            batch_size = 500
            for i in range(0, len(valid_rows), batch_size):
                batch = valid_rows[i:i + batch_size]
                cursor.executemany(sql, batch)
                streamed_rows += cursor.rowcount # MySQL reports 2 for updates, 1 for inserts
            
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Database Error: {e}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    duration = (datetime.now(timezone.utc) - stage_start).total_seconds()

    return {
        "total_lines": total_lines,
        "valid_rows": len(valid_rows),
        "invalid_rows": invalid_rows,
        "streamed_rows": len(valid_rows), # Using list count for simplicity
        "duration_seconds": duration
    }

if __name__ == "__main__":
    result = stage1_load_raw_mysql(
        local_file_path=Path('data/raw/jobstreet/2025-12-16_044220/dump.jsonl'),
        source="JobStreet",
        scrape_timestamp=datetime.now(timezone.utc),
        db_config=DB_CONFIG
    )
    print(result)