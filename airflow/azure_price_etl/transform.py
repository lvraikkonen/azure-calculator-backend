import csv
import json
import os
from datetime import datetime
import uuid
import time
from azure_price_etl.utils.helpers import (
    ensure_directory, normalize_price_unit, normalize_category
)

def transform_price_data(**context):
    """转换价格数据CSV为MongoDB文档"""
    ti = context['ti']
    fetch_result = ti.xcom_pull(task_ids='fetch_price_data', key='fetch_result')
    sync_id = ti.xcom_pull(task_ids='fetch_price_data', key='sync_id')
    
    if not fetch_result:
        raise ValueError("未找到上一步骤的数据")
    
    file_path = fetch_result['file_path']
    print(f"开始转换CSV文件: {file_path}")
    start_time = time.time()
    
    try:
        # 创建输出目录
        output_dir = ensure_directory("/tmp/azure_prices_transformed")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建输出文件
        products_file = f"{output_dir}/products_{timestamp}.json"
        history_file = f"{output_dir}/price_history_{timestamp}.json"
        
        # 处理批大小
        batch_size = 5000
        product_count = 0
        history_count = 0
        unique_products = set()  # 用于产品去重
        
        # 打开输出文件
        with open(products_file, 'w') as p_file, open(history_file, 'w') as h_file:
            # 写入JSON数组开始
            p_file.write('[\n')
            h_file.write('[\n')
            
            # 使用分块处理CSV
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                total_rows = 0
                products_written = 0
                history_written = 0
                
                for row in reader:
                    total_rows += 1
                    
                    # 生成产品代码和唯一键
                    product_id = str(uuid.uuid4())
                    product_base = row['productId'].split('/')[-1].lower()
                    if len(product_base) > 20:  # 限制长度
                        product_base = product_base[:20]
                        
                    location = row['location'].lower().replace(' ', '')
                    product_code = f"{product_base}-{location}"
                    product_key = f"{row['productName']}_{row['skuName']}_{row['location']}"
                    
                    # 跳过重复产品
                    if product_key in unique_products:
                        continue
                    unique_products.add(product_key)
                    
                    # 处理价格
                    try:
                        retail_price = float(row['retailPrice'])
                    except (ValueError, KeyError):
                        retail_price = 0.0
                    
                    # 创建产品文档
                    product = {
                        "_id": product_id,
                        "product_code": product_code,
                        "name": f"{row.get('productName', '')} ({row.get('skuName', '')})",
                        "description": f"{row.get('productName', '')} - {row.get('skuName', '')} 位于{row.get('location', '')}",
                        "price": retail_price,
                        "price_unit": normalize_price_unit(row.get('unitOfMeasure', ''), retail_price),
                        "category": normalize_category(row.get('serviceFamily', ''), row.get('serviceName', '')),
                        "region": row.get('location', ''),
                        "service_family": row.get('serviceFamily', ''),
                        "service_name": row.get('serviceName', ''),
                        "meter_id": row.get('meterId', ''),
                        "sku_id": row.get('skuId', ''),
                        "tier_minimum_units": int(row.get('tierMinimumUnits', 0)),
                        "unit_of_measure": row.get('unitOfMeasure', ''),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "metadata": {
                            "currency_code": row.get('currencyCode', ''),
                            "effective_start_date": row.get('effectiveStartDate', ''),
                            "is_primary_meter_region": row.get('isPrimaryMeterRegion', '') == 'TRUE',
                            "type": row.get('type', '')
                        }
                    }
                    
                    # 创建价格历史记录
                    history = {
                        "_id": str(uuid.uuid4()),
                        "product_code": product_code,
                        "product_id": product_id,
                        "price": retail_price,
                        "effective_date": datetime.now().isoformat(),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # 写入JSON（带逗号分隔）
                    if products_written > 0:
                        p_file.write(',\n')
                    p_file.write(json.dumps(product, ensure_ascii=False))
                    products_written += 1
                    
                    if history_written > 0:
                        h_file.write(',\n')
                    h_file.write(json.dumps(history, ensure_ascii=False))
                    history_written += 1
                    
                    # 打印进度
                    if total_rows % 1000 == 0:
                        print(f"已处理 {total_rows} 行，转换 {products_written} 个产品")
                    
                    # 限制处理的产品数量，避免内存问题
                    if products_written >= 10000:  # 限制处理10000条，根据需要调整
                        print(f"已达到最大记录数限制({products_written})，停止处理")
                        break
            
            # 写入JSON数组结束
            p_file.write('\n]')
            h_file.write('\n]')
        
        elapsed_time = time.time() - start_time
        
        # 返回结果
        result = {
            'sync_id': sync_id,
            'products_file': products_file,
            'history_file': history_file,
            'product_count': products_written,
            'history_count': history_written,
            'total_rows': total_rows,
            'elapsed_time': elapsed_time,
            'timestamp': datetime.now().isoformat()
        }
        
        ti.xcom_push(key='transform_result', value=result)
        print(f"转换完成: 处理 {total_rows} 行，生成 {products_written} 个产品，{history_written} 条历史记录")
        print(f"耗时: {elapsed_time:.2f} 秒")
        return result
        
    except Exception as e:
        error_msg = f"转换价格数据失败: {str(e)}"
        print(error_msg)
        ti.xcom_push(key='transform_error', value=error_msg)
        raise