from pymongo import MongoClient
from airflow.hooks.base import BaseHook
import time
from datetime import datetime

def validate_data(**context):
    """验证加载的数据"""
    ti = context['ti']
    load_result = ti.xcom_pull(task_ids='load_to_mongodb', key='load_result')
    sync_id = ti.xcom_pull(task_ids='fetch_price_data', key='sync_id')
    
    if not load_result:
        raise ValueError("未找到加载结果数据")
    
    print(f"开始验证MongoDB数据，同步ID: {sync_id}")
    start_time = time.time()
    
    # 获取MongoDB连接信息
    conn = BaseHook.get_connection('mongodb_default')
    mongodb_uri = f"mongodb://{conn.host}:{conn.port}/"
    db_name = conn.schema
    
    # 连接MongoDB
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    
    try:
        # 1. 验证产品数量
        product_count = db.azure_products.count_documents({})
        print(f"验证产品数量: 加载 {load_result['product_count']}, 实际 {product_count}")
        
        if product_count == 0:
            raise ValueError("产品集合为空，验证失败")
            
        # 2. 验证价格历史数量
        history_count = db.price_history.count_documents({"_id": {"$regex": sync_id}})
        print(f"验证历史记录: 期望至少有 1 条，实际 {history_count}")
        
        # 3. 验证价格有效性
        price_check = list(db.azure_products.find({"price": {"$lt": 0}}).limit(5))
        if price_check:
            print(f"警告：发现 {len(price_check)} 个产品价格为负值")
        
        # 4. 检查产品分类分布
        categories = db.azure_products.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
        
        print("产品分类统计:")
        for cat in categories:
            print(f"  - {cat['_id']}: {cat['count']} 个产品")
        
        # 5. 更新验证状态
        db.sync_metadata.update_one(
            {"_id": sync_id},
            {"$set": {
                "validated": True,
                "validation_time": datetime.now().isoformat(),
                "product_count": product_count,
                "history_count": history_count
            }}
        )
        
        elapsed_time = time.time() - start_time
        result = {
            'success': True,
            'product_count': product_count,
            'history_count': history_count,
            'duration_seconds': elapsed_time
        }
        
        print(f"数据验证成功，耗时: {elapsed_time:.2f} 秒")
        ti.xcom_push(key='validation_result', value=result)
        return result
        
    except Exception as e:
        error_msg = f"数据验证失败: {str(e)}"
        print(error_msg)
        
        # 更新同步状态
        db.sync_metadata.update_one(
            {"_id": sync_id},
            {"$set": {
                "validated": False,
                "validation_error": error_msg
            }}
        )
        
        ti.xcom_push(key='validation_error', value=error_msg)
        raise