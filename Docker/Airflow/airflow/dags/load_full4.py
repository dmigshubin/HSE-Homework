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
    'load_full',
    default_args=default_args,
    description='Load full data',
    schedule_interval='3 3 * * *',
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['postgres', 'Load', 'full']
)

def load_csv_to_raw(**context):
    hook = PostgresHook(postgres_conn_id='demo_db')
    hook.run('DROP TABLE IF EXISTS temperature_raw CASCADE; CREATE TABLE temperature_raw (id TEXT, room_id TEXT, noted_date TEXT, temp NUMERIC, out_in TEXT);')
    hook.copy_expert("COPY temperature_raw FROM STDIN WITH CSV HEADER", '/opt/airflow/dags/data/IOT-temp.csv')

load_csv_full = PythonOperator(task_id='load_csv_raw_full', python_callable=load_csv_to_raw, dag=dag)

transform_full = PostgresOperator(
    task_id='transform_full_historical',
    postgres_conn_id='demo_db',
    sql='''
    DROP TABLE IF EXISTS temperature_results;
    CREATE TABLE temperature_results AS
    WITH cleaned AS (
        SELECT TO_DATE(LEFT(TRIM(noted_date), 10), 'DD-MM-YYYY') AS noted_date, temp
        FROM temperature_raw WHERE out_in = 'In' AND temp IS NOT NULL
    ),
    p AS (SELECT percentile_cont(0.05) WITHIN GROUP (ORDER BY temp) AS p5,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY temp) AS p95 FROM cleaned)
    SELECT noted_date, temp FROM cleaned c CROSS JOIN p WHERE temp BETWEEN p.p5 AND p.p95;
    ''',
    dag=dag,
    autocommit=True
)

load_csv_full >> transform_full