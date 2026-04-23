import json
import mysql.connector
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from utils.schemas import RawJob, CleanedJob
from etl.cloud_function_main import transform_raw_to_cleaned


DB_CONFIG = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'job_data',
    'charset': 'utf8mb4'
}

def stage2_transform_clean_data(
    source: str,
    scrape_date: datetime,
    db_config: dict,
    batch_size: int = 500
) -> Dict[str, Any]:
    """Stage 2: MySQL Transform using existing transform_raw_to_cleaned logic."""
    start_time = datetime.now(timezone.utc)
    print(f"[Stage 2] Starting: source={source}, date={scrape_date.date()}")

    try:
        conn = mysql.connector.connect(**db_config)
        # Using dictionary=True allows row['payload'] access
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch raw data
        # We filter by date to match your daily scrape workflow
        query = """
            SELECT job_id, source, scrape_timestamp, payload 
            FROM raw_jobs 
            WHERE LOWER(source) = LOWER(%s) 
              AND DATE(scrape_timestamp) = DATE(%s)
        """
        cursor.execute(query, (source, scrape_date.date()))
        raw_rows = cursor.fetchall()
        
        total_raw = len(raw_rows)
        if total_raw == 0:
            print(f"[Stage 2] No rows found for {source} on {scrape_date.date()}")
            return {"status": "empty", "transformed": 0}

        cleaned_batch = []
        skipped_count = 0

        # 2. Transform using your existing function
        for row in raw_rows:
            # MySQL JSON columns return as dicts; ensure it's not a string
            payload = row['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)

            # Change row to RawJob dataclass for compatibility with transform function
            raw_job = RawJob(
                job_id=row['job_id'],
                source=row['source'],
                scrape_timestamp=row['scrape_timestamp'],
                payload=payload
            )

            # Re-wrap in a format your function accepts (dict or RawJob object)
            # Your function handles both, so passing the row dict is fine
            cleaned_job: CleanedJob = transform_raw_to_cleaned(raw_job)

            if cleaned_job:
                # Map dataclass to tuple for MySQL insert
                cleaned_batch.append((
                    cleaned_job.job_id,
                    cleaned_job.source,
                    cleaned_job.scrape_timestamp,
                    cleaned_job.job_url,
                    cleaned_job.job_title,
                    cleaned_job.job_description,
                    cleaned_job.job_location,
                    cleaned_job.job_classification,
                    cleaned_job.job_work_type,
                    cleaned_job.job_salary_min_sgd_raw,
                    cleaned_job.job_salary_max_sgd_raw,
                    cleaned_job.job_salary_type,
                    cleaned_job.job_salary_min_sgd_monthly,
                    cleaned_job.job_salary_max_sgd_monthly,
                    cleaned_job.job_currency,
                    cleaned_job.job_posted_timestamp,
                    cleaned_job.company_id,
                    cleaned_job.company_url,
                    cleaned_job.company_name,
                    cleaned_job.company_description,
                    cleaned_job.company_industry,
                    cleaned_job.company_size,
                ))

            else:
                skipped_count += 1

        # 3. Batch Upsert into cleaned_jobs
        if cleaned_batch:
            upsert_sql = """
                INSERT INTO cleaned_jobs
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for i in range(0, len(cleaned_batch), batch_size):
                batch = cleaned_batch[i : i + batch_size]
                cursor.executemany(upsert_sql, batch)
            
            conn.commit()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        print(f"[Stage 2] Done: {len(cleaned_batch)} loaded, {skipped_count} skipped ({duration:.1f}s)")

        return {
            "fetched": total_raw,
            "transformed": len(cleaned_batch),
            "skipped": skipped_count,
            "duration_seconds": duration
        }

    except mysql.connector.Error as err:
        print(f"Database error during Stage 2: {err}")
        raise
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    result = stage2_transform_clean_data(
        source="JobStreet",
        scrape_date=datetime(2025, 12, 16, tzinfo=timezone.utc),
        db_config=DB_CONFIG
    )
    print(result)