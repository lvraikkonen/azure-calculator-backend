from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import Optional, List, Dict, Any

from app.api.deps import get_current_user, get_rag_service
from app.models.user import User
from app.rag.services.hybrid_rag_service import HybridRAGService
from app.rag.core.models import Document, Metadata, QueryResult
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/query", response_model=QueryResult)
async def rag_query(
    query: str,
    top_k: Optional[int] = 5,
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    """
    执行RAG查询
    """
    try:
        logger.info(f"用户 {current_user.username} 执行RAG查询: {query}")
        result = await rag_service.query(query, top_k=top_k)
        return result
    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def add_document(
    content: str = Form(...),
    title: str = Form(...),
    source: str = Form(...),
    author: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    """
    添加文档到知识库
    """
    try:
        logger.info(f"用户 {current_user.username} 添加文档: {title}")
        
        metadata = Metadata(
            source=source,
            title=title,
            author=author,
            content_type=content_type
        )
        
        document = Document(content=content, metadata=metadata)
        doc_id = await rag_service.add_document(document)
        
        return {"id": doc_id, "status": "success", "message": "文档已添加"}
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加文档失败: {str(e)}"
        )

@router.post("/documents/web", status_code=status.HTTP_201_CREATED)
async def add_web_document(
    url: str,
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    """
    从网页URL添加文档到知识库
    """
    try:
        logger.info(f"用户 {current_user.username} 从URL添加文档: {url}")
        
        # 加载网页
        docs = await rag_service.web_loader.load(url)
        
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法从URL加载内容"
            )
        
        # 添加文档
        doc_ids = await rag_service.add_documents(docs)
        
        return {
            "ids": doc_ids, 
            "status": "success", 
            "message": f"成功添加 {len(doc_ids)} 个文档"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL添加文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从URL添加文档失败: {str(e)}"
        )

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    """
    从知识库删除文档
    """
    try:
        logger.info(f"用户 {current_user.username} 删除文档: {doc_id}")
        
        success = await rag_service.delete_document(doc_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在或删除失败"
            )
        
        return {"status": "success", "message": "文档已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )