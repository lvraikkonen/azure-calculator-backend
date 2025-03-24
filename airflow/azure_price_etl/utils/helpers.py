import time
from datetime import datetime
import os
import json
import uuid

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def generate_sync_id():
    """生成同步ID"""
    return str(uuid.uuid4())

def normalize_price_unit(unit_of_measure, price):
    """标准化价格单位格式"""
    if "Hour" in unit_of_measure:
        return f"¥{price}/小时"
    elif "Month" in unit_of_measure:
        return f"¥{price}/月"
    elif "GB" in unit_of_measure:
        return f"¥{price}/GB"
    else:
        return f"¥{price}/{unit_of_measure}"
        
def normalize_category(service_family, service_name):
    """标准化服务分类"""
    category_mapping = {
        "Compute": "计算",
        "Storage": "存储",
        "Networking": "网络",
        "Databases": "数据库",
        "Analytics": "分析",
        "AI + Machine Learning": "AI与机器学习",
        "Web": "Web服务"
    }
    
    if service_family in category_mapping:
        return category_mapping[service_family]
        
    # 二级映射
    if "database" in service_name.lower() or "sql" in service_name.lower():
        return "数据库"
    if "storage" in service_name.lower():
        return "存储"
    if "virtual" in service_name.lower() or "vm" in service_name.lower():
        return "计算"
            
    return service_family  # 默认使用原始服务族名称