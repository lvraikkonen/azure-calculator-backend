import json
import time
import os
from datetime import datetime
from pymongo import MongoClient, UpdateOne
from airflow.hooks.base import BaseHook

def load_price_data(**context):
    """加载转换后的数据到MongoDB"""
    ti = context['ti']
    transform_result = ti.xcom_pull(task_ids='transform_price_data', key='transform_result')
    sync_id = ti.xcom_pull(task_ids='fetch_price_data', key='sync_id')
    
    if not transform_result:
        raise ValueError("未找到转换结果数据")
    
    print(f"开始加载数据到MongoDB，同步ID: {sync_id}")
    start_time = time.time()
    
    # 获取MongoDB连接信息
    conn = BaseHook.get_connection('mongodb_default')
    mongodb_uri = f"mongodb://{conn.host}:{conn.port}/"
    db_name = conn.schema
    
    # 连接MongoDB
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    
    try:
        # 读取产品数据
        print(f"读取产品数据文件: {transform_result['products_file']}")
        with open(transform_result['products_file'], 'r') as f:
            products = json.load(f)
        
        # 读取价格历史
        print(f"读取历史数据文件: {transform_result['history_file']}")
        with open(transform_result['history_file'], 'r') as f:
            price_history = json.load(f)
        
        # 使用版本化方式处理集合
        # 1. 创建临时集合
        staging_collection_name = f"azure_products_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"创建临时集合: {staging_collection_name}")
        
        # 2. 批量插入数据到临时集合
        if products:
            batch_size = 1000
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                db[staging_collection_name].insert_many(batch)
                print(f"已插入 {i + len(batch)} / {len(products)} 产品记录")
            
            # 3. 创建索引
            print("为临时集合创建索引")
            db[staging_collection_name].create_index("product_code", unique=True)
            db[staging_collection_name].create_index("category")
            db[staging_collection_name].create_index("region")
            db[staging_collection_name].create_index("service_family")
        
        # 4. 插入价格历史
        if price_history:
            print(f"插入 {len(price_history)} 条价格历史记录")
            for i in range(0, len(price_history), batch_size):
                batch = price_history[i:i + batch_size]
                db.price_history.insert_many(batch)
                print(f"已插入 {i + len(batch)} / {len(price_history)} 历史记录")
        
        # 5. 原子方式切换集合（实现蓝绿部署）
        old_collection_name = None
        if 'azure_products' in db.list_collection_names():
            # 重命名现有集合为历史集合
            old_collection_name = f"azure_products_old_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"重命名当前集合为: {old_collection_name}")
            db.command('renameCollection', f'{db_name}.azure_products', 
                      'to': f'{db_name}.{old_collection_name}')
        
        # 重命名临时集合为主集合
        print(f"将临时集合 {staging_collection_name} 重命名为 azure_products")
        db.command('renameCollection', f'{db_name}.{staging_collection_name}', 
                  'to': f'{db_name}.azure_products')
        
        # 6. 记录同步元数据
        end_time = datetime.now()
        sync_metadata = {
            '_id': sync_id,
            'sync_type': 'azure_prices',
            'status': 'success',
            'start_time': datetime.now(),
            'end_time': end_time,
            'duration_seconds': (time.time() - start_time),
            'record_count': len(products),
            'download_url': transform_result.get('download_url', ''),
            'error_message': None,
            'old_collection': old_collection_name
        }
        
        db.sync_metadata.insert_one(sync_metadata)
        
        # 清理临时文件
        try:
            os.remove(transform_result['products_file'])
            os.remove(transform_result['history_file'])
            print("临时文件清理完成")
        except Exception as e:
            print(f"清理临时文件失败: {e}")
        
        # 返回结果
        elapsed_time = time.time() - start_time
        result = {
            'success': True,
            'sync_id': sync_id,
            'product_count': len(products),
            'history_count': len(price_history),
            'duration_seconds': elapsed_time
        }
        
        print(f"成功加载数据到MongoDB: {len(products)} 产品, {len(price_history)} 历史记录")
        print(f"耗时: {elapsed_time:.2f} 秒")
        ti.xcom_push(key='load_result', value=result)
        return result
        
    except Exception as e:
        error_msg = f"加载数据到MongoDB失败: {str(e)}"
        print(error_msg)
        
        # 记录失败信息
        db.sync_metadata.insert_one({
            '_id': sync_id,
            'sync_type': 'azure_prices',
            'status': 'failed',
            'start_time': datetime.now(),
            'end_time': datetime.now(),
            'duration_seconds': (time.time() - start_time),
            'record_count': 0,
            'error_message': error_msg
        })
        
        ti.xcom_push(key='load_error', value=error_msg)
        raise