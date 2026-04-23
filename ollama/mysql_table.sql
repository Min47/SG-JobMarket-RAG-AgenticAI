CREATE DATABASE IF NOT EXISTS job_data;

USE job_data;

-- 1. Raw Jobs Table
CREATE TABLE IF NOT EXISTS raw_jobs (
    job_id VARCHAR(100) PRIMARY KEY,
    source VARCHAR(50),
    scrape_timestamp DATETIME(6),
    payload JSON,
    INDEX (source),
    INDEX (scrape_timestamp)
);

-- 2. Cleaned Jobs Table
CREATE TABLE cleaned_jobs (
    job_id VARCHAR(100),
    source VARCHAR(50),
    scrape_timestamp DATETIME(6),
    job_url TEXT,
    job_title VARCHAR(255),
    job_description TEXT,
    job_location VARCHAR(100),
    job_classification VARCHAR(255),
    job_work_type VARCHAR(100),
    job_salary_min_raw DECIMAL(10, 2),
    job_salary_max_raw DECIMAL(10, 2),
    job_salary_type VARCHAR(50),
    job_salary_min_monthly DECIMAL(10, 2),
    job_salary_max_monthly DECIMAL(10, 2),
    job_currency VARCHAR(10),
    job_posted_timestamp DATETIME(6),
    company_id VARCHAR(100),
    company_url TEXT,
    company_name VARCHAR(255),
    company_description TEXT,
    company_industry VARCHAR(255),
    company_size VARCHAR(100),
    CONSTRAINT job PRIMARY KEY (job_id, scrape_timestamp),
    INDEX (source),
    INDEX (scrape_timestamp)
);