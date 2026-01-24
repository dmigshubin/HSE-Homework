from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

with DAG(
    dag_id='extract',
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    history = PostgresOperator(
        task_id='extract_json',
        postgres_conn_id='demo_db', # Идентификатор соединения
        sql='''create table extract_demo.data_from_json as 
                    select 
                      post.value->>'name' as name,
                      post.value->>'species' as species,
                      post.value->>'favFoods' as favFoods,
                      post.value->>'birthYear' as birthYear,
                      post.value->>'photo' as photo
                    from extract_demo.json_source_data,
                    jsonb_array_elements(json_data->'pets') as post(value);
        ''',
    )