from uuid import UUID
from typing import Union
from ldap3 import Server, Connection, core
from fastapi import HTTPException
from app.core.config import get_settings, Settings
from app.core.logging import logger

settings = get_settings()

def search_ldap_user_in_ad(
    username: str,
    settings: Settings
) -> dict:
    """LDAP用户搜索工具函数"""
    # 日志记录配置信息
    logger.debug(f"LDAP查询开始 | 用户: {username}")
    logger.debug(f"LDAP配置 | 服务器: {settings.LDAP_SERVER} | 端口: {settings.LDAP_PORT}")
    logger.debug(f"LDAP配置 | 域: {settings.LDAP_DOMAIN} | 基础DN: {settings.LDAP_BASE_DN}")
    logger.debug(f"LDAP配置 | 绑定DN: {settings.LDAP_BIND_DN}")
    
    try:
        # 使用配置的管理员账号
        bind_cn = settings.LDAP_BIND_DN.split(',')[0].split('=')[1]
        
        # 使用UPN格式构造认证字符串
        user_principal = f"{bind_cn}@{settings.LDAP_DOMAIN}"
        admin_pwd = settings.LDAP_BIND_PASSWORD
        
        logger.debug(f"LDAP认证 | 使用UPN: {user_principal}")
        
        # 创建服务器连接
        server = Server(settings.LDAP_SERVER, port=settings.LDAP_PORT)
        logger.debug(f"LDAP服务器连接创建成功: {server}")
        
        logger.debug("尝试LDAP绑定...")
        conn = Connection(
            server,
            user=user_principal,
            password=admin_pwd,
            auto_bind=True
        )
        
        logger.debug(f"LDAP绑定状态: {'成功' if conn.bound else '失败'}")
        logger.debug(f"LDAP连接对象: {conn}")
        
        # 执行搜索
        search_filter = f"(sAMAccountName={username})"
        logger.debug(f"LDAP搜索 | 基础DN: {settings.LDAP_BASE_DN} | 过滤器: {search_filter}")
        
        search_result = conn.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=search_filter,
            attributes=['objectGUID', 'sAMAccountName', 'mail', 'displayName', 'memberOf']
        )
        
        logger.debug(f"LDAP搜索结果: {search_result} | 条目数: {len(conn.entries)}")

        if not conn.entries:
            logger.warning(f"未找到AD用户: {username}")
            raise HTTPException(status_code=404, detail="AD用户不存在")

        entry = conn.entries[0]
        logger.debug(f"找到用户: {entry.sAMAccountName.value}")
        
        return {
            "username": entry.sAMAccountName.value,
            "displayname": entry.displayName.value,
            "guid": entry.objectGUID.value,
            "email": entry.mail.value if 'mail' in entry else None,
            "groups": ",".join(entry.memberOf.values) if entry.memberOf else ""
        }
            
    except core.exceptions.LDAPBindError as bind_err:
        # 详细记录认证失败信息
        logger.error(f"LDAP认证失败: {str(bind_err)}")
        logger.error(f"LDAP服务器: {settings.LDAP_SERVER} | 绑定DN: {settings.LDAP_BIND_DN}")
        raise HTTPException(401, f"LDAP认证失败: {str(bind_err)}")
    except Exception as e:
        logger.error(f"AD查询失败: {type(e).__name__} - {str(e)}")
        logger.exception("AD查询异常详情:")
        raise HTTPException(500, f"AD查询失败: {str(e)}")
    finally:
        # 确保连接关闭
        if 'conn' in locals() and conn.bound:
            logger.debug("关闭LDAP连接")
            conn.unbind()

def format_ad_guid(raw_guid: Union[bytes, str]) -> str:
    """标准化AD GUID格式"""
    try:
        if isinstance(raw_guid, bytes):
            return str(UUID(bytes_le=raw_guid))
        elif isinstance(raw_guid, str):
            clean_guid = raw_guid.strip('{}')
            return str(UUID(clean_guid))
        else:
            raise ValueError("不支持的GUID格式")
    except Exception as e:
        logger.error(f"GUID格式转换失败: {raw_guid} - {str(e)}")
        raise HTTPException(400, "无效的LDAP GUID格式")