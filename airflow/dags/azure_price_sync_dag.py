from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.http_sensor import HttpSensor
from airflow.utils.dates import days_ago
from airflow.models import Variable

# 导入ETL组件
from azure_price_etl.fetch import fetch_price_data
from azure_price_etl.transform import transform_price_data
from azure_price_etl.load import load_price_data
from azure_price_etl.validate import validate_data

# DAG定义
default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'email': ['admin@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'azure_price_sync',
    default_args=default_args,
    description='同步Azure价格数据到MongoDB',
    schedule_interval='0 2 * * *',  # 每天凌晨2点运行
    start_date=days_ago(1),
    catchup=False,
    tags=['azure', 'pricing', 'etl'],
)

# 检查API可用性
check_api = HttpSensor(
    task_id='check_api_availability',
    http_conn_id='azure_price_api',
    endpoint='/api/retail/pricesheet/download?api-version=2023-06-01-preview',
    response_check=lambda response: response.status_code == 200,
    poke_interval=60,  # 每60秒检查一次
    timeout=600,  # 超时时间10分钟
    dag=dag,
)

# 备份MongoDB集合
backup_mongodb = BashOperator(
    task_id='backup_mongodb',
    bash_command='mongodump --db azure_calculator --collection azure_products --archive=/tmp/mongodb_backup_$(date +%Y%m%d).gz --gzip || echo "Backup skipped"',
    dag=dag,
)

# 获取价格数据
fetch_data = PythonOperator(
    task_id='fetch_price_data',
    python_callable=fetch_price_data,
    op_kwargs={'api_version': '2023-06-01-preview'},
    dag=dag,
)

# 转换价格数据
transform_data = PythonOperator(
    task_id='transform_price_data',
    python_callable=transform_price_data,
    dag=dag,
)

# 加载数据到MongoDB
load_to_mongodb = PythonOperator(
    task_id='load_to_mongodb',
    python_callable=load_price_data,
    dag=dag,
)

# 验证数据
validate_data_task = PythonOperator(
    task_id='validate_data',
    python_callable=validate_data,
    dag=dag,
)

# 任务依赖关系
check_api >> backup_mongodb >> fetch_data >> transform_data >> load_to_mongodb >> validate_data_task