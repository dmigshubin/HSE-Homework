from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
from pymongo import MongoClient
import pandas as pd
import json
from sqlalchemy import create_engine, text

def replicate_user_sessions():
    print("Connecting to MongoDB")

    mongo_client = MongoClient("mongodb://root:password@mongodb:27017/")
    db = mongo_client["analytics"]

    sessions = list(db["UserSessions"].find())

    if not sessions:
        print("Нет данных для репликации.")
        return

    print("Fetched sessions:", len(sessions))

    df = pd.DataFrame(sessions)

    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)

    df["pages_visited"] = df.get("pages_visited", []).apply(lambda x: x if isinstance(x, list) else [])
    df["actions"] = df.get("actions", []).apply(lambda x: x if isinstance(x, list) else [])

    print("Connecting to Postgres")

    engine = create_engine(
        "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"
    )

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT,
        start_time TIMESTAMPTZ,
        end_time TIMESTAMPTZ,
        pages_visited TEXT[],
        device TEXT,
        actions TEXT[]
    );
    """

    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        conn.execute(text("DELETE FROM user_sessions"))

    print("Writing to Postgres")

    df.to_sql("user_sessions", engine, if_exists="append", index=False)

    print(f"Inserted {len(df)} sessions into user_sessions")

    mongo_client.close()

def replicate_support_tickets():
    print("Connecting to MongoDB for SupportTickets")

    mongo_client = MongoClient("mongodb://root:password@mongodb:27017/")
    db = mongo_client["analytics"]

    tickets = list(db["SupportTickets"].find())

    if not tickets:
        print("Нет данных для SupportTickets.")
        return

    df = pd.DataFrame(tickets)

    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)

    df["resolution_minutes"] = (df["updated_at"] - df["created_at"]).dt.total_seconds() / 60
    engine = create_engine("postgresql+psycopg2://airflow:airflow@postgres:5432/airflow")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id TEXT PRIMARY KEY,
        user_id TEXT,
        status TEXT,
        issue_type TEXT,
        messages JSONB,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ,
        resolution_minutes DOUBLE PRECISION
);
    """
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        conn.execute(text("DELETE FROM support_tickets"))

    if "messages" in df.columns:
        df["messages"] = df["messages"].apply(lambda x: json.dumps(x, default=str) if isinstance(x, list) else '[]')

    engine.execute(text("DROP MATERIALIZED VIEW IF EXISTS airflow.support_tickets_summary CASCADE; DROP TABLE IF EXISTS airflow.support_tickets CASCADE"))

    df.to_sql("support_tickets", engine, if_exists="replace", index=False)
    print(f"Inserted {len(df)} SupportTickets")
    mongo_client.close()

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    "mongo_to_postgres_with_vitrinas",
    default_args=default_args,
    description="Replicate MongoDB to Postgres and refresh analytic views",
    schedule_interval="@once",
    start_date=datetime(2026, 3, 9),
    catchup=False
) as dag:

    replicate_sessions_task = PythonOperator(
        task_id="replicate_user_sessions",
        python_callable=replicate_user_sessions
    )

    replicate_tickets_task = PythonOperator(
        task_id="replicate_support_tickets",
        python_callable=replicate_support_tickets
    )

    # Витрина 1: Активность пользователей
    create_user_activity = PostgresOperator(
        task_id="create_user_activity_summary",
        postgres_conn_id="postgres_default",
        sql="""
        CREATE MATERIALIZED VIEW IF NOT EXISTS user_activity_summary AS
        SELECT
            user_id,
            COUNT(session_id) AS total_sessions,
            AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60) AS avg_session_minutes,
            SUM(COALESCE(array_length(pages_visited,1),0)) AS total_pages_visited,
            SUM(COALESCE(array_length(actions,1),0)) AS total_actions,
            MAX(end_time) AS last_activity
        FROM user_sessions
        GROUP BY user_id;
        """
    )

    refresh_user_activity = PostgresOperator(
        task_id="refresh_user_activity_summary",
        postgres_conn_id="postgres_default",
        sql="REFRESH MATERIALIZED VIEW user_activity_summary;"
    )

    # Витрина 2: Статистика по тикетам поддержки
    create_support_tickets = PostgresOperator(
        task_id="create_support_tickets_summary",
        postgres_conn_id="postgres_default",
        sql="""
        CREATE MATERIALIZED VIEW IF NOT EXISTS support_tickets_summary AS
        SELECT
            status,
            issue_type,
            COUNT(*) AS ticket_count,
            AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/60) AS avg_resolution_minutes
        FROM support_tickets
        GROUP BY status, issue_type;
        """
    )

    refresh_support_tickets = PostgresOperator(
        task_id="refresh_support_tickets_summary",
        postgres_conn_id="postgres_default",
        sql="REFRESH MATERIALIZED VIEW support_tickets_summary;"
    )

    # Зависимости
    replicate_sessions_task >> create_user_activity >> refresh_user_activity
    replicate_tickets_task >> create_support_tickets >> refresh_support_tickets