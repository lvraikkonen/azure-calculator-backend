import requests
import os
import json
from datetime import datetime
import time
from azure_price_etl.utils.helpers import ensure_directory, generate_sync_id

def fetch_price_data(**context):
    """从Azure API获取价格数据CSV"""
    ti = context['ti']
    sync_id = generate_sync_id()
    ti.xcom_push(key='sync_id', value=sync_id)
    
    api_version = context.get('api_version', '2023-06-01-preview')
    url = f"https://prices.azure.cn/api/retail/pricesheet/download?api-version={api_version}"
    
    print(f"开始从Azure获取价格数据: {url}")
    start_time = time.time()
    
    try:
        # 请求下载URL
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        download_url = data.get("DownloadUrl")
        if not download_url:
            error_msg = "API响应中未找到下载URL"
            ti.xcom_push(key='fetch_error', value=error_msg)
            raise ValueError(error_msg)
        
        # 流式下载CSV文件以处理大文件
        with requests.get(download_url, stream=True) as csv_response:
            csv_response.raise_for_status()
            
            # 创建临时目录
            output_dir = ensure_directory("/tmp/azure_prices")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"{output_dir}/azure_prices_{timestamp}.csv"
            
            # 分块写入文件
            with open(file_path, 'wb') as f:
                chunk_size = 8192  # 8KB
                total_size = 0
                for chunk in csv_response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        
                        # 每10MB打印一次进度
                        if total_size % (10 * 1024 * 1024) < chunk_size:
                            print(f"已下载 {total_size / (1024 * 1024):.2f} MB")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
        # 计算处理时间
        elapsed_time = time.time() - start_time
        
        # 推送结果
        result = {
            'sync_id': sync_id,
            'file_path': file_path,
            'file_size': file_size,
            'download_url': download_url,
            'elapsed_time': elapsed_time,
            'timestamp': datetime.now().isoformat()
        }
        ti.xcom_push(key='fetch_result', value=result)
        
        print(f"成功下载Azure价格数据: {file_path}")
        print(f"文件大小: {file_size/1024/1024:.2f} MB, 耗时: {elapsed_time:.2f} 秒")
        return result
        
    except Exception as e:
        error_msg = f"获取Azure价格数据失败: {str(e)}"
        print(error_msg)
        ti.xcom_push(key='fetch_error', value=error_msg)
        raise