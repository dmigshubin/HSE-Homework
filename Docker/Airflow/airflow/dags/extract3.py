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
    'transform',
    default_args=default_args,
    description='Extract data from json',
    schedule_interval='3 3 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['postgres', '3NF']
)

def load_csv_to_raw(**context):
    csv_path = '/opt/airflow/dags/data/IOT-temp.csv'
    df = pd.read_csv(csv_path)
    if len(df.columns) != 5:
        df.columns = ['id', 'room_id', 'noted_date', 'temp', 'out_in']

    hook = PostgresHook(postgres_conn_id='demo_db')
    hook.run('''DROP TABLE IF EXISTS temperature_raw; CREATE TABLE temperature_raw (id TEXT, room_id TEXT, noted_date TEXT, temp NUMERIC, out_in TEXT)''')
    hook.copy_expert(
        sql="COPY temperature_raw FROM STDIN WITH CSV HEADER",
        filename='/opt/airflow/dags/data/IOT-temp.csv'
    )

load_csv = PythonOperator(
    task_id='load_csv_file',
    python_callable=load_csv_to_raw,
    dag=dag)

transform_temp = PostgresOperator(
    task_id='process_temperature',
    postgres_conn_id='demo_db',
    sql='''
    DROP TABLE IF EXISTS temperature_results;
    CREATE TABLE temperature_results AS
    WITH cleaned AS (
        SELECT TO_DATE(LEFT(noted_date, 10), 'DD-MM-YYYY') AS noted_date, temp
        FROM temperature_raw WHERE out_in = 'In'
    ),
    p AS (
        SELECT percentile_cont(0.05) WITHIN GROUP (ORDER BY temp) AS p5,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY temp) AS p95
        FROM cleaned
    )
    SELECT noted_date, temp FROM cleaned c, p 
    WHERE temp BETWEEN p5 AND p95
    ORDER BY temp DESC LIMIT 5;  -- топ-5
    ''',
    dag=dag
)

load_csv >> transform_temp