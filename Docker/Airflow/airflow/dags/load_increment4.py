from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd

default_args = {
    'owner': 'shubindmitrii',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'load_delta',
    default_args=default_args,
    description='Delta load last 7 days',
    schedule_interval='0 4 * * *',  # После full_load (4:00)
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['postgres', 'Load', 'delta']
)

transform_delta = PostgresOperator(
    task_id='transform_delta',
    postgres_conn_id='demo_db',
    sql='''
    INSERT INTO temperature_results (noted_date, temp)
    SELECT noted_date, temp FROM (
        WITH cleaned AS (
            SELECT TO_DATE(LEFT(TRIM(noted_date), 10), 'DD-MM-YYYY') AS noted_date, temp
            FROM temperature_raw 
            WHERE out_in = 'In' AND temp IS NOT NULL
            AND TO_DATE(LEFT(TRIM(noted_date), 10), 'DD-MM-YYYY') >= CURRENT_DATE - INTERVAL '7 days'
        ),
        p AS (
            SELECT 
                GREATEST(MIN(temp), -1000) AS p5,
                LEAST(MAX(temp), 1000) AS p95
            FROM cleaned WHERE cleaned.temp IS NOT NULL
        )
        SELECT noted_date, temp FROM cleaned c CROSS JOIN p WHERE temp BETWEEN p.p5 AND p.p95
    ) delta;
    ''',
    dag=dag
)
