"""
Database utility functions for market cycle detection data storage
"""

import os
import logging
import psycopg2
from psycopg2 import OperationalError, sql
from psycopg2.extras import execute_values
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# Database connection parameters (override via environment; no secrets in code)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Connection retry parameters
MAX_RETRIES = 5
RETRY_INTERVAL = 5


def get_connection():
    """Establish database connection with retry logic"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("Connected to PostgreSQL")
            return conn
        except OperationalError as e:
            logger.error(f"Connection failed (attempt {retries + 1}/{MAX_RETRIES}): {e}")
            retries += 1
            if retries < MAX_RETRIES:
                import time
                time.sleep(RETRY_INTERVAL)
    raise Exception(f"Unable to establish a connection after {MAX_RETRIES} retries")


def ensure_tables_exist():
    """Create tables if they don't exist"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Table for raw FRED series data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_cycle_raw_data (
                    date DATE NOT NULL,
                    series_name VARCHAR(100) NOT NULL,
                    value DOUBLE PRECISION,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, series_name)
                );
            """)
            
            # Table for transformed series data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_cycle_transformed_data (
                    date DATE NOT NULL,
                    series_name VARCHAR(100) NOT NULL,
                    value DOUBLE PRECISION,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, series_name)
                );
            """)
            
            # Table for composite scores and phase classifications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_cycle_composite (
                    date DATE NOT NULL PRIMARY KEY,
                    composite_score DOUBLE PRECISION,
                    composite_smoothed DOUBLE PRECISION,
                    slope DOUBLE PRECISION,
                    phase VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Table for S&P 500 YoY data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_cycle_sp500 (
                    date DATE NOT NULL PRIMARY KEY,
                    sp500_yoy_pct DOUBLE PRECISION,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_raw_data_series 
                ON market_cycle_raw_data(series_name, date);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transformed_data_series 
                ON market_cycle_transformed_data(series_name, date);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_composite_date 
                ON market_cycle_composite(date DESC);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sp500_date 
                ON market_cycle_sp500(date DESC);
            """)
            
            conn.commit()
            logger.info("Database tables and indexes created/verified")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_raw_data(df: pd.DataFrame):
    """Save raw FRED series data to database"""
    if df.empty:
        logger.warning("No raw data to save")
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Prepare data for bulk insert
            data_to_insert = []
            for date in df.index:
                for col in df.columns:
                    value = df.loc[date, col]
                    if pd.notna(value):
                        data_to_insert.append((date.date(), col, float(value)))
            
            if data_to_insert:
                insert_query = """
                    INSERT INTO market_cycle_raw_data (date, series_name, value)
                    VALUES %s
                    ON CONFLICT (date, series_name)
                    DO UPDATE SET value = EXCLUDED.value, created_at = CURRENT_TIMESTAMP;
                """
                execute_values(cursor, insert_query, data_to_insert)
                conn.commit()
                logger.info(f"Saved {len(data_to_insert)} raw data records to database")
    except Exception as e:
        logger.error(f"Error saving raw data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_transformed_data(df: pd.DataFrame):
    """Save transformed series data to database"""
    if df.empty:
        logger.warning("No transformed data to save")
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Prepare data for bulk insert
            data_to_insert = []
            for date in df.index:
                for col in df.columns:
                    value = df.loc[date, col]
                    if pd.notna(value):
                        data_to_insert.append((date.date(), col, float(value)))
            
            if data_to_insert:
                insert_query = """
                    INSERT INTO market_cycle_transformed_data (date, series_name, value)
                    VALUES %s
                    ON CONFLICT (date, series_name)
                    DO UPDATE SET value = EXCLUDED.value, created_at = CURRENT_TIMESTAMP;
                """
                execute_values(cursor, insert_query, data_to_insert)
                conn.commit()
                logger.info(f"Saved {len(data_to_insert)} transformed data records to database")
    except Exception as e:
        logger.error(f"Error saving transformed data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_composite_data(comp: pd.Series, comp_sm: pd.Series, slope: pd.Series, phase: pd.Series):
    """Save composite scores and phase classifications to database"""
    if comp.empty:
        logger.warning("No composite data to save")
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Prepare data for bulk insert
            data_to_insert = []
            for date in comp.index:
                comp_val = comp.loc[date] if pd.notna(comp.loc[date]) else None
                comp_sm_val = comp_sm.loc[date] if pd.notna(comp_sm.loc[date]) else None
                slope_val = slope.loc[date] if pd.notna(slope.loc[date]) else None
                phase_val = phase.loc[date] if pd.notna(phase.loc[date]) else None
                
                if comp_val is not None or comp_sm_val is not None:
                    data_to_insert.append((
                        date.date(),
                        float(comp_val) if comp_val is not None else None,
                        float(comp_sm_val) if comp_sm_val is not None else None,
                        float(slope_val) if slope_val is not None else None,
                        str(phase_val) if phase_val is not None else None
                    ))
            
            if data_to_insert:
                insert_query = """
                    INSERT INTO market_cycle_composite (date, composite_score, composite_smoothed, slope, phase)
                    VALUES %s
                    ON CONFLICT (date)
                    DO UPDATE SET 
                        composite_score = EXCLUDED.composite_score,
                        composite_smoothed = EXCLUDED.composite_smoothed,
                        slope = EXCLUDED.slope,
                        phase = EXCLUDED.phase,
                        created_at = CURRENT_TIMESTAMP;
                """
                execute_values(cursor, insert_query, data_to_insert)
                conn.commit()
                logger.info(f"Saved {len(data_to_insert)} composite data records to database")
    except Exception as e:
        logger.error(f"Error saving composite data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_sp500_data(spx_yoy: pd.Series):
    """Save S&P 500 YoY data to database"""
    if spx_yoy.empty:
        logger.warning("No S&P 500 data to save")
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Prepare data for bulk insert
            data_to_insert = []
            for date in spx_yoy.index:
                value = spx_yoy.loc[date]
                if pd.notna(value):
                    data_to_insert.append((date.date(), float(value)))
            
            if data_to_insert:
                insert_query = """
                    INSERT INTO market_cycle_sp500 (date, sp500_yoy_pct)
                    VALUES %s
                    ON CONFLICT (date)
                    DO UPDATE SET 
                        sp500_yoy_pct = EXCLUDED.sp500_yoy_pct,
                        created_at = CURRENT_TIMESTAMP;
                """
                execute_values(cursor, insert_query, data_to_insert)
                conn.commit()
                logger.info(f"Saved {len(data_to_insert)} S&P 500 records to database")
    except Exception as e:
        logger.error(f"Error saving S&P 500 data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

