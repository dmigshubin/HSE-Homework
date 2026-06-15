import logging
import pendulum
from airflow.models.dag import DAG
from airflow.decorators import task
from airflow.providers.yandex.hooks.yandex import YandexCloudBaseHook
from airflow.exceptions import AirflowSkipException
from yandexcloud.operations import OperationError

FOLDER_ID = 'b1gkrtfjs01vjjk7ehpp'
SERVICE_ACCOUNT_ID = 'ajea0b4qmhro95ac2b35'
SUBNET_IDS = ['e9bidtkgp6mmtfc357fb']
SECURITY_GROUP_IDS = ['default-sg-enpmjifgf5qjjl35g04c']

JOB_NAME = 'reviews_data_job'
JOB_SCRIPT = 's3a://bucket-342/scripts/job.py'
JOB_ARGS = []
JOB_PROPERTIES = {
    'spark.executor.instances': '1',
}


@task
def create_cluster(yc_hook, cluster_spec):
    """1 этап: создание кластера Managed Spark"""
    spark_client = yc_hook.sdk.wrappers.Spark()
    spark_client.create_cluster(cluster_spec)
    return spark_client.cluster_id


@task
def run_spark_job(yc_hook, cluster_id, job_spec):
    """2 этап: запуск PySpark-задания"""
    spark_client = yc_hook.sdk.wrappers.Spark()
    try:
        job_operation = spark_client.create_pyspark_job(cluster_id=cluster_id, spec=job_spec)
        job_id = job_operation.response.id
        job_info = job_operation.response
    except OperationError as job_error:
        job_id = job_error.operation_result.meta.job_id
        job_info, _ = spark_client.get_job(cluster_id=cluster_id, job_id=job_id)
        raise
    finally:
        job_log = spark_client.get_job_log(cluster_id=cluster_id, job_id=job_id)
        for line in job_log:
            logging.info(line)
        logging.info("Job info: %s", job_info)


@task(trigger_rule="all_done")
def delete_cluster(yc_hook, cluster_id):
    """3 этап: удаление кластера"""
    if cluster_id:
        spark_client = yc_hook.sdk.wrappers.Spark()
        spark_client.delete_cluster(cluster_id=cluster_id)
    else:
        raise AirflowSkipException("cluster_id is empty; nothing to delete")


# Настройки DAG
with DAG(
        dag_id="credit_data_processing",
        start_date=pendulum.datetime(2026, 6, 15),
        schedule=None,  # запуск вручную
) as dag:
    yc_hook = YandexCloudBaseHook()

    cluster_spec = yc_hook.sdk.wrappers.SparkClusterParameters(
        folder_id=FOLDER_ID,
        service_account_id=SERVICE_ACCOUNT_ID,
        subnet_ids=SUBNET_IDS,
        security_group_ids=SECURITY_GROUP_IDS,
        driver_pool_resource_preset="c2-m8",
        driver_pool_size=1,
        executor_pool_resource_preset="c4-m16",
        executor_pool_min_size=1,
        executor_pool_max_size=2,
    )

    cluster_id = create_cluster(yc_hook, cluster_spec)

    job_spec = yc_hook.sdk.wrappers.PysparkJobParameters(
        name=JOB_NAME,
        main_python_file_uri=JOB_SCRIPT,
        args=JOB_ARGS,
        properties=JOB_PROPERTIES,
    )

    task_job = run_spark_job(yc_hook, cluster_id, job_spec)
    task_delete = delete_cluster(yc_hook, cluster_id)

    task_job >> task_delete
