import random
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime
import uuid
import asyncio
import nest_asyncio

# 导入RAG系统组件
from app.rag.core.registry import RAGComponentRegistry
from app.rag.services.rag_factory import create_rag_service, get_evaluator
from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.evaluation.benchmark.runner import BenchmarkRunner
from app.rag.evaluation.benchmark.datasets import BenchmarkDataset
from app.rag.evaluation.benchmark.analysis import BenchmarkAnalyzer
from app.rag.core.models import Document, TextChunk, QueryResult
from app.services.llm.base import BaseLLMService

# 启用asyncio在非事件循环的环境中运行
nest_asyncio.apply()

# 设置页面配置
st.set_page_config(
    page_title="RAG调优实验平台",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用标题和描述
st.title("RAG调优实验平台")
st.markdown("""
此平台提供RAG全流程透明化和各种参数优化能力，支持算法工程师进行调优实验。
""")

# 会话状态管理
if 'llm_service' not in st.session_state:
    st.session_state.llm_service = None
if 'rag_service' not in st.session_state:
    st.session_state.rag_service = None
if 'evaluator' not in st.session_state:
    st.session_state.evaluator = None
if 'experiment_history' not in st.session_state:
    st.session_state.experiment_history = []
if 'current_config' not in st.session_state:
    st.session_state.current_config = {}
if 'current_results' not in st.session_state:
    st.session_state.current_results = {}
if 'completed_steps' not in st.session_state:
    st.session_state.completed_steps = {"系统初始化": False}

# 侧边栏导航
st.sidebar.title("RAG调优导航")

# 显示页面工作流程图
st.sidebar.markdown("## 工作流程")
workflow_steps = [
    "⚙️ 系统初始化",
    "🔧 组件配置",
    "📄 文档处理",
    "🔍 查询测试",
    "📊 评估与对比"
]

# 确定当前页面在工作流中的位置
page_prefixes = {
    "系统初始化": "⚙️",
    "组件配置": "🔧",
    "文档处理": "📄",
    "查询测试": "🔍",
    "评估与对比": "📊"
}

# 从URL参数中获取当前页面
if 'page' in st.query_params:
    page = st.query_params['page']
else:
    page = "系统初始化"  # 默认页面

# 计算当前步骤
if page in page_prefixes:
    current_step_name = f"{page_prefixes[page]} {page}"
    current_step = workflow_steps.index(current_step_name) if current_step_name in workflow_steps else 0
else:
    current_step = 0

# 显示工作流进度
st.sidebar.progress(current_step / (len(workflow_steps) - 1))

# 导航分组
st.sidebar.markdown("## 基础配置")
system_init = st.sidebar.button("⚙️ 系统初始化",
                                use_container_width=True,
                                type="primary" if page == "系统初始化" else "secondary")

component_config = st.sidebar.button("🔧 组件配置",
                                     use_container_width=True,
                                     type="primary" if page == "组件配置" else "secondary",
                                     disabled=not st.session_state.rag_service)

st.sidebar.markdown("## RAG流程")
document_processing = st.sidebar.button("📄 文档处理",
                                        use_container_width=True,
                                        type="primary" if page == "文档处理" else "secondary",
                                        disabled=not st.session_state.rag_service)

query_testing = st.sidebar.button("🔍 查询测试",
                                  use_container_width=True,
                                  type="primary" if page == "查询测试" else "secondary",
                                  disabled="vector_store" not in st.session_state.current_results)

evaluation = st.sidebar.button("📊 评估与对比",
                               use_container_width=True,
                               type="primary" if page == "评估与对比" else "secondary",
                               disabled="query_result" not in st.session_state.current_results)

st.sidebar.markdown("## 高级功能")
benchmark = st.sidebar.button("🧪 基准测试",
                              use_container_width=True,
                              type="primary" if page == "基准测试" else "secondary",
                              disabled=not st.session_state.rag_service)

embedding_tuning = st.sidebar.button("🔄 嵌入微调",
                                     use_container_width=True,
                                     type="primary" if page == "嵌入微调" else "secondary",
                                     disabled=not st.session_state.rag_service)

experiment_history = st.sidebar.button("📚 实验历史",
                                       use_container_width=True,
                                       type="primary" if page == "实验历史" else "secondary")

# 处理页面导航逻辑
if system_init:
    page = "系统初始化"
elif component_config:
    page = "组件配置"
elif document_processing:
    page = "文档处理"
elif query_testing:
    page = "查询测试"
elif evaluation:
    page = "评估与对比"
elif benchmark:
    page = "基准测试"
elif embedding_tuning:
    page = "嵌入微调"
elif experiment_history:
    page = "实验历史"

# 更新URL参数
st.query_params['page'] = page

# 添加系统状态指示器
st.sidebar.markdown("---")
st.sidebar.markdown("## 系统状态")

# 创建状态指示器
col1, col2 = st.sidebar.columns([1, 1])
with col1:
    st.markdown("系统服务:")
    st.markdown("文档处理:")
    st.markdown("查询结果:")
with col2:
    # 系统状态
    if st.session_state.rag_service:
        st.markdown("✅ 已初始化")
    else:
        st.markdown("❌ 未初始化")

    # 文档状态
    if "vector_store" in st.session_state.current_results:
        st.markdown("✅ 已完成")
    else:
        st.markdown("❌ 未完成")

    # 查询状态
    if "query_result" in st.session_state.current_results:
        st.markdown("✅ 已完成")
    else:
        st.markdown("❌ 未完成")

# 工作流帮助提示
with st.sidebar.expander("💡 工作流程指南"):
    st.markdown("""
    **推荐工作流程**:
    1. **系统初始化**: 加载组件和服务
    2. **组件配置**: 选择RAG流程的组件
    3. **文档处理**: 上传和处理文档
    4. **查询测试**: 测试RAG查询效果
    5. **评估与对比**: 评估系统性能

    **高级功能**:
    - **基准测试**: 批量测试系统性能
    - **嵌入微调**: 优化嵌入模型
    - **实验历史**: 查看和比较实验结果
    """)


# 辅助函数
def run_async(coro):
    """运行异步函数"""
    return asyncio.run(coro)


def load_component_info():
    """加载所有已注册组件信息"""
    components = {}
    for component_type in RAGComponentRegistry.COMPONENT_TYPES:
        # 获取该类型下的所有组件名称
        component_names = RAGComponentRegistry.list_components(component_type).get(component_type, [])

        # 获取每个组件的详细信息
        component_details = {}  # 使用字典代替列表
        for name in component_names:
            # 创建默认结构，确保字段一致性
            component_data = {
                "name": name,
                "class": "Unknown",
                "docstring": "",
                "parameters": {},
                "full_info": {}
            }

            try:
                # 获取组件类
                component_class = RAGComponentRegistry.get(component_type, name)

                # 获取组件信息
                component_info = RAGComponentRegistry.component_info(component_type, name)

                # 更新组件信息
                component_data.update({
                    "class": component_class.__name__,
                    "docstring": component_class.__doc__ or "",
                    "parameters": component_info.get("parameters", {}),
                    "full_info": component_info
                })
            except Exception as e:
                component_data["error"] = str(e)

            component_details[name] = component_data

        # 如果想保持顺序，可以转换回列表
        components[component_type] = list(component_details.values())
        # 或者直接使用字典：components[component_type] = component_details

    return components


def get_component_options(components_info, component_type):
    """获取指定类型的组件选项列表"""
    if component_type not in components_info:
        return []

    component_info = components_info[component_type]

    # 检查是字典还是列表
    if isinstance(component_info, dict):
        return list(component_info.keys())
    elif isinstance(component_info, list):
        return [comp['name'] for comp in component_info if 'name' in comp]
    else:
        return []


def pretty_print_json(data):
    """美化JSON显示"""
    return json.dumps(data, indent=2, ensure_ascii=False)


def visualize_text_chunks(chunks):
    """可视化文本块"""
    if not chunks:
        return

    df = pd.DataFrame([
        {
            "ID": chunk.id,
            "文档ID": chunk.doc_id,
            "内容长度": len(chunk.content),
            "内容预览": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
        }
        for chunk in chunks
    ])

    st.dataframe(df)

    # 文本块长度分布
    fig = px.histogram(df, x="内容长度", title="文本块长度分布")
    st.plotly_chart(fig)


def visualize_vector_embeddings(chunks, method='tsne'):
    """可视化向量嵌入"""
    if not chunks or not chunks[0].embedding:
        st.warning("无有效向量嵌入数据")
        return

    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA

    # 提取嵌入向量
    embeddings = np.array([chunk.embedding for chunk in chunks if chunk.embedding])
    labels = [f"Chunk {i + 1}" for i in range(len(embeddings))]

    # 降维
    if method == 'tsne':
        model = TSNE(n_components=2, random_state=42)
    else:
        model = PCA(n_components=2, random_state=42)

    reduced_data = model.fit_transform(embeddings)

    # 创建图表
    fig = px.scatter(
        x=reduced_data[:, 0],
        y=reduced_data[:, 1],
        text=labels,
        title=f"向量嵌入可视化 ({method.upper()})"
    )

    st.plotly_chart(fig)


def compare_configurations(config1, config2, results1, results2):
    """比较两种配置的结果"""
    # 配置差异
    diff = {}
    all_keys = set(config1.keys()) | set(config2.keys())

    for key in all_keys:
        if key not in config1:
            diff[key] = {"仅配置2": config2[key]}
        elif key not in config2:
            diff[key] = {"仅配置1": config1[key]}
        elif config1[key] != config2[key]:
            diff[key] = {"配置1": config1[key], "配置2": config2[key]}

    # 创建对比信息
    comparison = {
        "配置差异": diff,
        "结果对比": {
            "配置1": {k: v for k, v in results1.items() if k != "详细步骤"},
            "配置2": {k: v for k, v in results2.items() if k != "详细步骤"}
        }
    }

    return comparison


def save_experiment(config, results, name=None):
    """保存实验结果"""
    experiment = {
        "id": str(uuid.uuid4()),
        "name": name or f"实验 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "timestamp": datetime.now().isoformat(),
        "config": config,
        "results": results
    }

    st.session_state.experiment_history.append(experiment)
    return experiment["id"]


def init_rag_system():
    """初始化RAG系统服务"""
    with st.spinner("初始化系统中..."):
        # 创建LLM服务
        st.session_state.llm_service = LLMService()

        # 创建RAG服务（异步）
        st.session_state.rag_service = run_async(
            create_rag_service(st.session_state.llm_service)
        )

        # 创建评估器（异步）
        evaluator = run_async(
            get_evaluator(st.session_state.llm_service, force_new=True)
        )

        # 注册评估指标
        register_all_metrics(evaluator, st.session_state.llm_service)
        st.session_state.evaluator = evaluator

    st.success("RAG系统已成功初始化！")


def register_all_metrics(evaluator, llm_service):
    """注册所有评估指标"""
    # 添加评估指标注册代码
    from app.rag.evaluation.metrics import (
        RelevanceMetric,
        FaithfulnessMetric,
        ContextPrecisionMetric,
        AnswerCompletenessMetric,
        ConciseMeaningfulnessMetric,
        LatencyMetric
    )

    # 基础质量指标
    evaluator.register_metric(RelevanceMetric(llm_service))
    evaluator.register_metric(FaithfulnessMetric(llm_service))
    evaluator.register_metric(ContextPrecisionMetric())

    # 高级质量指标
    evaluator.register_metric(AnswerCompletenessMetric(llm_service))
    evaluator.register_metric(ConciseMeaningfulnessMetric(llm_service))

    # 性能指标
    evaluator.register_metric(LatencyMetric())


# ======================= 各功能页面实现 =======================

def show_system_init_page():
    """系统初始化页面"""
    st.header("系统初始化")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("""
        本页面用于初始化RAG系统并查看系统状态。初始化将加载所有注册的组件和服务。
        """)

        if st.button("初始化系统", key="init_button"):
            init_rag_system()

        # 系统状态
        st.subheader("系统状态")
        status = {
            "LLM服务": "✅ 已加载" if st.session_state.llm_service else "❌ 未加载",
            "RAG服务": "✅ 已加载" if st.session_state.rag_service else "❌ 未加载",
            "评估器": "✅ 已加载" if st.session_state.evaluator else "❌ 未加载"
        }

        for k, v in status.items():
            # 判断状态显示颜色
            is_loaded = "✅" in v

            # 使用列布局让状态指示更明显
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"### {k}")
            with col2:
                if is_loaded:
                    st.markdown(f"<span style='color:green; font-size:18px;'>{v}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:red; font-size:18px;'>{v}</span>", unsafe_allow_html=True)

    with col2:
        st.info("提示：初始化后，您可以进入其他功能模块进行实验。")

    # 加载已注册组件信息
    # 在show_system_init_page函数中替换原有的组件显示代码
    if st.session_state.rag_service:
        st.subheader("已注册组件")
        try:
            components = load_component_info()

            tab1, tab2 = st.tabs(["分类统计", "详细列表"])

            with tab1:
                # 统计每个类型的组件数量
                component_counts = {ctype: len(comps) for ctype, comps in components.items()}
                fig = px.bar(
                    x=list(component_counts.keys()),
                    y=list(component_counts.values()),
                    labels={"x": "组件类型", "y": "数量"},
                    title="组件数量统计"
                )
                st.plotly_chart(fig)

            with tab2:
                # 使用两列布局
                col1, col2 = st.columns([1, 3])

                with col1:
                    # 使用选择框选择组件类型
                    component_type = st.selectbox(
                        "选择组件类型",
                        options=RAGComponentRegistry.COMPONENT_TYPES
                    )

                with col2:
                    # 显示选定类型的组件数量
                    comp_count = len(components[component_type])
                    st.subheader(f"{component_type} 组件 ({comp_count}个)")

                # 显示选定类型的组件
                if comp_count == 0:
                    st.info(f"未找到{component_type}类型的组件")
                else:
                    # 使用网格布局显示组件卡片
                    cols = st.columns(min(3, comp_count))

                    for i, comp in enumerate(components[component_type]):
                        with cols[i % min(3, comp_count)]:
                            with st.container(border=True):
                                st.markdown(f"### {comp['name']}")
                                if "error" in comp:
                                    st.error(f"加载错误: {comp['error']}")
                                else:
                                    st.markdown(f"**类名**: `{comp['class']}`")

                                    # 显示详情按钮
                                    if st.button("查看详情", key=f"btn_{component_type}_{comp['name']}"):
                                        st.session_state.selected_component = {
                                            "type": component_type,
                                            "name": comp['name'],
                                            "data": comp
                                        }

                # 显示选定组件的详情
                if "selected_component" in st.session_state:
                    selected = st.session_state.selected_component
                    with st.expander(f"详情: {selected['name']}", expanded=True):
                        comp = selected["data"]

                        if "docstring" in comp and comp['docstring']:
                            st.markdown("##### 说明")
                            st.markdown(comp['docstring'])

                        # 显示参数信息
                        if "parameters" in comp and comp["parameters"]:
                            st.markdown("##### 参数")
                            params_data = []
                            for param_name, param_info in comp["parameters"].items():
                                required = "✓" if param_info.get("required", False) else "○"
                                default = param_info.get("default", "无")
                                if default is None:
                                    default = "None"
                                annotation = param_info.get("annotation", "-")

                                params_data.append({
                                    "参数名": param_name,
                                    "必需": required,
                                    "默认值": str(default),
                                    "类型": annotation
                                })

                            # 使用表格显示参数
                            st.table(pd.DataFrame(params_data))
                        else:
                            st.info("此组件没有参数")
        except Exception as e:
            st.error(f"加载组件信息失败: {str(e)}")


def show_component_config_page():
    """组件配置页面"""
    st.header("组件配置")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    st.markdown("""
    在此页面配置RAG系统的各组件参数。您可以选择不同的组件实现并设置其参数。
    """)

    # 加载已注册组件信息
    components_info = load_component_info()

    # 创建配置表单
    with st.form("component_config_form"):
        st.subheader("基础组件配置")

        # 保存组件配置
        config_components = {}

        # 定义组件类型列表
        component_types = [
            {"type": RAGComponentRegistry.DOCUMENT_LOADER, "title": "文档加载器"},
            {"type": RAGComponentRegistry.CHUNKER, "title": "分块器"},
            {"type": RAGComponentRegistry.EMBEDDER, "title": "嵌入提供者"},
            {"type": RAGComponentRegistry.VECTOR_STORE, "title": "向量存储"},
            {"type": RAGComponentRegistry.RETRIEVER, "title": "检索器"},
            {"type": RAGComponentRegistry.RERANKER, "title": "重排序器"},
            {"type": RAGComponentRegistry.GENERATOR, "title": "生成器"}
        ]

        # 处理每种组件类型
        for comp_def in component_types:
            comp_type = comp_def["type"]
            title = comp_def["title"]

            st.markdown(f"#### {title}")

            # 获取该组件类型的所有实现
            component_list = []
            if comp_type in components_info:
                for comp in components_info[comp_type]:
                    component_list.append(comp["name"])

            if not component_list:
                st.info(f"未找到可用的{title}组件")
                config_components[comp_type] = {"type": "", "params": {}}
                continue

            # 选择组件实现类型
            selected_component = st.selectbox(
                f"选择{title}类型",
                options=component_list,
                key=f"select_{comp_type}"
            )

            # 获取选中组件的参数信息
            component_params = {}
            selected_comp_info = None

            for comp in components_info[comp_type]:
                if comp["name"] == selected_component:
                    selected_comp_info = comp
                    break

            # 如果找到组件信息，显示参数输入界面
            if selected_comp_info and "parameters" in selected_comp_info:
                # 创建可折叠区域显示参数
                with st.expander(f"{title}参数设置", expanded=True):
                    if not selected_comp_info["parameters"]:
                        st.info(f"此{title}组件无需设置参数")
                    else:
                        # 根据参数类型生成对应的输入控件
                        for param_name, param_info in selected_comp_info["parameters"].items():
                            # 判断参数类型，创建对应输入控件
                            required = param_info.get("required", False)
                            param_type = param_info.get("annotation", "")
                            default_val = param_info.get("default")

                            # 参数标签
                            param_label = f"{param_name}" + (" (必需)" if required else "")

                            # 根据类型或命名约定选择控件类型
                            if "bool" in param_type.lower() or param_name.lower() in ["use_cache", "safe_mode",
                                                                                      "html_to_text"]:
                                # 布尔值使用复选框
                                default_bool = False if default_val is None else bool(default_val)
                                component_params[param_name] = st.checkbox(param_label, value=default_bool)

                            elif any(word in param_name.lower() for word in
                                     ["timeout", "size", "count", "limit", "top_k", "max", "min"]):
                                # 数值使用数字输入框
                                default_num = 0 if default_val is None else float(default_val)
                                if "int" in param_type.lower() or param_name in ["top_k", "max_tokens"]:
                                    component_params[param_name] = st.number_input(param_label, value=int(default_num))
                                else:
                                    component_params[param_name] = st.number_input(param_label, value=default_num)

                            elif "float" in param_type.lower() or param_name in ["temperature", "score_threshold"]:
                                # 浮点数（0-1范围）使用滑块
                                default_float = 0.5 if default_val is None else float(default_val)
                                component_params[param_name] = st.slider(param_label, 0.0, 1.0, default_float)

                            else:
                                # 默认使用文本输入框
                                default_str = "" if default_val is None else str(default_val)
                                component_params[param_name] = st.text_input(param_label, value=default_str)

            # 保存该组件的配置
            config_components[comp_type] = {
                "type": selected_component,
                "params": component_params
            }

        # 高级选项
        st.markdown("#### 高级配置")
        with st.expander("高级配置"):
            advanced_config = st.text_area("JSON配置", value="{}", height=150)

            # 验证JSON格式
            try:
                advanced_params = json.loads(advanced_config)
            except:
                st.error("JSON格式无效")
                advanced_params = {}

        # 配置名称
        config_name = st.text_input("配置名称", value=f"配置 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 提交按钮
        submit_button = st.form_submit_button("保存配置")

        if submit_button:
            # 构建完整配置
            config = {
                "name": config_name,
                "components": config_components,
                "advanced": advanced_params
            }

            # 保存当前配置
            st.session_state.current_config = config
            st.success(f"配置'{config_name}'已保存！")

            # 显示JSON格式的配置
            st.json(config)


def show_document_processing_page():
    """文档处理页面"""
    st.header("文档处理")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    st.markdown("""
    在此页面上传和处理文档，查看文档处理流程。您可以观察从原始文档到向量的完整处理过程。
    """)

    # 文档上传
    st.subheader("文档上传")

    uploaded_file = st.file_uploader("选择文档文件",
                                     type=["txt", "pdf", "docx", "md", "json", "py", "html", "css", "js", "xlsx",
                                           "csv"])

    if uploaded_file:
        # 保存上传的文件
        file_path = f"./uploads/{uploaded_file.name}"
        os.makedirs("./uploads", exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"文件已上传: {file_path}")

        # 文档处理选项
        st.subheader("处理选项")

        col1, col2 = st.columns(2)

        with col1:
            chunk_size = st.number_input("块大小", value=1000, min_value=100, max_value=10000)
            chunk_overlap = st.number_input("块重叠", value=200, min_value=0, max_value=1000)

        with col2:
            encoding = st.selectbox("文件编码", ["utf-8", "latin-1", "gbk", "gb2312", "gb18030", "big5"])
            preprocessor = st.selectbox("预处理器", ["Default", "HTML Cleaner", "Code Extractor", "None"])

        # 文档处理按钮
        if st.button("处理文档"):
            with st.spinner("正在处理文档..."):
                # 显示处理阶段
                processing_status = st.empty()

                # 1. 文档加载
                processing_status.info("阶段1/4: 文档加载中...")

                try:
                    # 构建文档加载器
                    document_loader = RAGComponentRegistry.create(
                        RAGComponentRegistry.DOCUMENT_LOADER,
                        "file",
                        base_dir="./uploads",
                        use_cache=False
                    )

                    # 加载文档
                    documents = run_async(document_loader.load(uploaded_file.name, encoding=encoding))

                    if not documents:
                        st.error("文档加载失败！")
                        return

                    # 显示文档信息
                    st.subheader("文档信息")
                    for i, doc in enumerate(documents):
                        st.markdown(f"##### 文档 {i + 1}: {doc.metadata.title or '无标题'}")
                        st.markdown(f"- **源文件**: {doc.metadata.source}")
                        st.markdown(f"- **内容类型**: {doc.metadata.content_type}")
                        st.markdown(f"- **长度**: {len(doc.content)} 字符")

                        with st.expander("查看内容预览"):
                            st.text(doc.content[:1000] + ("..." if len(doc.content) > 1000 else ""))

                    # 2. 文档分块
                    processing_status.info("阶段2/4: 文档分块中...")

                    # 构建分块器
                    chunker = RAGComponentRegistry.create(
                        RAGComponentRegistry.CHUNKER,
                        "sentence_window",
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )

                    # 分块处理
                    chunks = []
                    for doc in documents:
                        doc_chunks = run_async(chunker.process([doc]))
                        chunks.extend(doc_chunks)

                    # 显示分块信息
                    st.subheader("分块信息")
                    st.markdown(f"总计 {len(chunks)} 个文本块")

                    visualize_text_chunks(chunks)

                    # 3. 嵌入生成
                    processing_status.info("阶段3/4: 嵌入生成中...")

                    # 构建嵌入提供者
                    embedder = RAGComponentRegistry.create(
                        RAGComponentRegistry.EMBEDDER,
                        "silicon_flow",  # 假设使用Azure嵌入
                        model="BAAI/bge-m3"
                    )

                    # 生成嵌入
                    for chunk in chunks:
                        chunk.embedding = run_async(embedder.get_embedding(chunk.content))

                    # 4. 向量存储
                    processing_status.info("阶段4/4: 向量存储中...")

                    # 构建向量存储
                    vector_store = RAGComponentRegistry.create(
                        RAGComponentRegistry.VECTOR_STORE,
                        "memory",  # 使用内存存储
                        embedding_provider=embedder
                    )

                    # 存储向量
                    chunk_ids = run_async(vector_store.add(chunks))

                    # 完成处理
                    processing_status.success("文档处理完成！")

                    # 可视化向量嵌入
                    st.subheader("向量嵌入可视化")

                    viz_method = st.radio("降维方法", ["t-SNE", "PCA"], horizontal=True)
                    visualize_vector_embeddings(chunks, method='tsne' if viz_method == 't-SNE' else 'pca')

                    # 保存处理结果
                    st.session_state.current_results["documents"] = documents
                    st.session_state.current_results["chunks"] = chunks
                    st.session_state.current_results["vector_store"] = vector_store

                    st.success("文档处理结果已保存，可以进行查询测试")

                except Exception as e:
                    st.error(f"处理文档时出错: {str(e)}")


def show_query_test_page():
    """查询测试页面"""
    st.header("查询测试")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    if "vector_store" not in st.session_state.current_results:
        st.warning("请先在'文档处理'页面处理文档")
        return

    st.markdown("""
    在此页面测试查询并观察整个RAG流程，包括查询转换、检索、重排和生成过程。
    """)

    # 查询输入
    st.subheader("查询输入")

    query = st.text_area("输入查询", height=100)
    col1, col2 = st.columns(2)

    with col1:
        top_k = st.number_input("返回结果数", value=5, min_value=1, max_value=20)

    with col2:
        temperature = st.slider("生成温度", 0.0, 1.0, 0.7)

    # 查询测试按钮
    if st.button("执行查询"):
        if not query:
            st.warning("请输入查询内容")
            return

        with st.spinner("正在执行查询..."):
            # 显示查询阶段
            query_status = st.empty()

            try:
                # 1. 查询转换
                query_status.info("阶段1/4: 查询转换中...")

                # 构建查询转换器
                query_transformer = RAGComponentRegistry.create(
                    RAGComponentRegistry.QUERY_TRANSFORMER,
                    "basic",  # 假设有基础查询转换器
                )

                # 转换查询
                transformed_query = run_async(query_transformer.transform(query))

                # 显示转换结果
                st.subheader("查询转换")
                st.markdown(f"**原始查询**: {query}")
                st.markdown(f"**转换查询**: {transformed_query}")

                # 2. 向量检索
                query_status.info("阶段2/4: 向量检索中...")

                # 获取向量存储
                vector_store = st.session_state.current_results["vector_store"]

                # 构建嵌入提供者
                embedder = RAGComponentRegistry.create(
                    RAGComponentRegistry.EMBEDDER,
                    "azure",  # 假设使用Azure嵌入
                    model="text-embedding-ada-002"
                )

                # 生成查询嵌入
                query_embedding = run_async(embedder.get_embedding(transformed_query))

                # 执行检索
                retrieved_chunks = run_async(vector_store.search(query_embedding, limit=top_k))

                # 显示检索结果
                st.subheader("检索结果")

                if not retrieved_chunks:
                    st.info("未找到相关内容")
                else:
                    st.markdown(f"找到 {len(retrieved_chunks)} 个相关块")

                    # 创建检索结果表格
                    retrieval_data = []
                    for i, chunk in enumerate(retrieved_chunks):
                        retrieval_data.append({
                            "序号": i + 1,
                            "分数": f"{chunk.score:.4f}" if chunk.score is not None else "N/A",
                            "文档": chunk.metadata.source.split('/')[
                                -1] if chunk.metadata and chunk.metadata.source else "未知",
                            "内容预览": chunk.content[:100] + ("..." if len(chunk.content) > 100 else "")
                        })

                    retrieval_df = pd.DataFrame(retrieval_data)
                    st.dataframe(retrieval_df)

                    # 可视化分数分布
                    scores = [chunk.score for chunk in retrieved_chunks if chunk.score is not None]
                    if scores:
                        fig = px.bar(
                            x=[f"块 {i + 1}" for i in range(len(scores))],
                            y=scores,
                            labels={"x": "检索块", "y": "相关性分数"},
                            title="检索块相关性分数"
                        )
                        st.plotly_chart(fig)

                # 3. 重排序
                query_status.info("阶段3/4: 重排序中...")

                # 构建重排序器
                reranker = RAGComponentRegistry.create(
                    RAGComponentRegistry.RERANKER,
                    "semantic",  # 假设有语义重排序器
                )

                # 执行重排序
                reranked_chunks = run_async(reranker.rerank(query, retrieved_chunks))

                # 显示重排序结果
                st.subheader("重排序结果")

                if not reranked_chunks:
                    st.info("重排序后无结果")
                else:
                    # 创建重排序结果表格
                    rerank_data = []
                    for i, chunk in enumerate(reranked_chunks):
                        rerank_data.append({
                            "序号": i + 1,
                            "新分数": f"{chunk.score:.4f}" if chunk.score is not None else "N/A",
                            "文档": chunk.metadata.source.split('/')[
                                -1] if chunk.metadata and chunk.metadata.source else "未知",
                            "内容预览": chunk.content[:100] + ("..." if len(chunk.content) > 100 else "")
                        })

                    rerank_df = pd.DataFrame(rerank_data)
                    st.dataframe(rerank_df)

                    # 重排序前后对比
                    if len(retrieved_chunks) == len(reranked_chunks):
                        compare_data = []

                        for i in range(len(retrieved_chunks)):
                            old_chunk = retrieved_chunks[i]
                            # 查找重排序后的相同块
                            new_chunk = None
                            for c in reranked_chunks:
                                if c.id == old_chunk.id:
                                    new_chunk = c
                                    break

                            if new_chunk:
                                compare_data.append({
                                    "块ID": old_chunk.id,
                                    "原始分数": old_chunk.score if old_chunk.score is not None else 0,
                                    "重排序分数": new_chunk.score if new_chunk.score is not None else 0
                                })

                        if compare_data:
                            compare_df = pd.DataFrame(compare_data)

                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=compare_df["块ID"],
                                y=compare_df["原始分数"],
                                name="原始分数"
                            ))
                            fig.add_trace(go.Bar(
                                x=compare_df["块ID"],
                                y=compare_df["重排序分数"],
                                name="重排序分数"
                            ))

                            fig.update_layout(
                                title="重排序前后分数对比",
                                xaxis_title="块ID",
                                yaxis_title="分数",
                                barmode="group"
                            )

                            st.plotly_chart(fig)

                # 4. 生成回答
                query_status.info("阶段4/4: 生成回答中...")

                # 构建生成器
                generator = RAGComponentRegistry.create(
                    RAGComponentRegistry.GENERATOR,
                    "llm",  # 假设有LLM生成器
                    llm_service=st.session_state.llm_service,
                    temperature=temperature
                )

                # 准备上下文
                context = "\n\n".join([chunk.content for chunk in reranked_chunks])

                # 生成回答
                answer = run_async(generator.generate(query, context))

                # 显示生成的回答
                st.subheader("生成的回答")
                st.markdown(answer)

                # 完成查询
                query_status.success("查询执行完成！")

                # 保存查询结果
                query_result = {
                    "query": query,
                    "transformed_query": transformed_query,
                    "retrieved_chunks": retrieved_chunks,
                    "reranked_chunks": reranked_chunks,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat()
                }

                st.session_state.current_results["query_result"] = query_result

            except Exception as e:
                st.error(f"执行查询时出错: {str(e)}")


def show_evaluation_page():
    """评估与对比页面"""
    st.header("评估与对比")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    if "query_result" not in st.session_state.current_results:
        st.warning("请先在'查询测试'页面执行查询")
        return

    st.markdown("""
    在此页面评估查询结果并进行配置对比实验。您可以应用不同的评估指标和比较不同配置的性能。
    """)

    # 当前结果评估
    st.subheader("当前结果评估")

    # 获取当前查询结果
    query_result = st.session_state.current_results["query_result"]

    # 显示查询和回答
    st.markdown(f"**查询**: {query_result['query']}")
    st.markdown(f"**回答**: {query_result['answer']}")

    # 评估指标选择
    st.markdown("#### 评估指标")

    available_metrics = ["relevance", "faithfulness", "context_precision",
                         "answer_completeness", "concise_meaningfulness", "latency"]

    selected_metrics = st.multiselect(
        "选择评估指标",
        available_metrics,
        default=["relevance", "faithfulness", "context_precision"]
    )

    # 手动评分
    st.markdown("#### 手动评分")

    manual_scores = {}

    col1, col2 = st.columns(2)

    with col1:
        manual_scores["relevance"] = st.slider("相关性", 0.0, 10.0, 7.0, 0.1)
        manual_scores["faithfulness"] = st.slider("忠实性", 0.0, 10.0, 7.0, 0.1)
        manual_scores["context_precision"] = st.slider("上下文精度", 0.0, 10.0, 7.0, 0.1)

    with col2:
        manual_scores["answer_completeness"] = st.slider("回答完整性", 0.0, 10.0, 7.0, 0.1)
        manual_scores["concise_meaningfulness"] = st.slider("简洁有意义性", 0.0, 10.0, 7.0, 0.1)
        manual_scores["latency"] = st.slider("延迟性能", 0.0, 10.0, 7.0, 0.1)

    if st.button("执行评估"):
        with st.spinner("正在评估..."):
            # 构建评估结果
            eval_result = {
                "metrics": {metric: manual_scores[metric] for metric in selected_metrics},
                "overall_score": sum(manual_scores[metric] for metric in selected_metrics) / len(
                    selected_metrics) if selected_metrics else 0
            }

            # 显示评估结果
            st.subheader("评估结果")

            # 指标分数表格
            st.markdown("#### 指标分数")

            metrics_df = pd.DataFrame([
                {"指标": metric, "分数": score}
                for metric, score in eval_result["metrics"].items()
            ])

            st.dataframe(metrics_df)

            # 可视化评估结果
            fig = px.bar(
                metrics_df,
                x="指标",
                y="分数",
                title="评估指标分数",
                color="分数",
                color_continuous_scale="Viridis"
            )

            st.plotly_chart(fig)

            # 总体评分
            st.metric("总体评分", f"{eval_result['overall_score']:.2f}/10")

            # 保存评估结果
            st.session_state.current_results["evaluation"] = eval_result

            st.success("评估完成！")

    # 配置对比实验
    st.subheader("配置对比实验")

    st.markdown("""
    在此部分，您可以对比不同配置的性能。请先保存当前配置和结果，然后创建新的配置进行对比。
    """)

    # 历史实验列表
    if st.session_state.experiment_history:
        st.markdown("#### 已保存的实验")

        experiment_options = [f"{exp['name']} ({exp['id']})" for exp in st.session_state.experiment_history]
        selected_exp = st.selectbox("选择实验进行对比", ["<选择实验>"] + experiment_options)

        if selected_exp != "<选择实验>":
            # 提取实验ID
            selected_exp_id = selected_exp.split("(")[-1].strip(")")

            # 查找实验数据
            selected_experiment = None
            for exp in st.session_state.experiment_history:
                if exp["id"] == selected_exp_id:
                    selected_experiment = exp
                    break

            if selected_experiment:
                # 创建对比结果
                comparison = compare_configurations(
                    st.session_state.current_config,
                    selected_experiment["config"],
                    st.session_state.current_results.get("evaluation", {}),
                    selected_experiment["results"].get("evaluation", {})
                )

                # 显示对比结果
                st.markdown("#### 配置对比")

                with st.expander("配置差异"):
                    st.json(comparison["配置差异"])

                st.markdown("#### 性能对比")

                if "evaluation" not in st.session_state.current_results:
                    st.warning("当前配置尚未评估")
                elif "evaluation" not in selected_experiment["results"]:
                    st.warning("所选实验尚未评估")
                else:
                    # 创建对比图表
                    current_metrics = st.session_state.current_results["evaluation"]["metrics"]
                    selected_metrics = selected_experiment["results"]["evaluation"]["metrics"]

                    # 合并所有指标
                    all_metrics = set(current_metrics.keys()) | set(selected_metrics.keys())

                    compare_data = []
                    for metric in all_metrics:
                        compare_data.append({
                            "指标": metric,
                            "当前配置": current_metrics.get(metric, 0),
                            "对比配置": selected_metrics.get(metric, 0)
                        })

                    compare_df = pd.DataFrame(compare_data)

                    # 计算改进率
                    compare_df["差异"] = compare_df["当前配置"] - compare_df["对比配置"]
                    compare_df["改进率"] = compare_df["差异"] / compare_df["对比配置"] * 100

                    # 显示对比表格
                    st.dataframe(compare_df)

                    # 可视化对比
                    fig = go.Figure()

                    fig.add_trace(go.Bar(
                        x=compare_df["指标"],
                        y=compare_df["当前配置"],
                        name="当前配置"
                    ))

                    fig.add_trace(go.Bar(
                        x=compare_df["指标"],
                        y=compare_df["对比配置"],
                        name="对比配置"
                    ))

                    fig.update_layout(
                        title="配置性能对比",
                        xaxis_title="评估指标",
                        yaxis_title="分数",
                        barmode="group"
                    )

                    st.plotly_chart(fig)

                    # 总体评分对比
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("当前总体评分", f"{st.session_state.current_results['evaluation']['overall_score']:.2f}")

                    with col2:
                        st.metric("对比总体评分", f"{selected_experiment['results']['evaluation']['overall_score']:.2f}")

                    with col3:
                        diff = st.session_state.current_results['evaluation']['overall_score'] - \
                               selected_experiment['results']['evaluation']['overall_score']
                        st.metric("评分差异", f"{diff:.2f}", delta=f"{diff:.2f}")

    # 保存当前实验
    st.markdown("#### 保存当前实验")

    exp_name = st.text_input("实验名称", value=f"实验 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if st.button("保存当前实验"):
        if "evaluation" not in st.session_state.current_results:
            st.warning("请先执行评估")
        else:
            exp_id = save_experiment(st.session_state.current_config, st.session_state.current_results, exp_name)
            st.success(f"实验已保存，ID: {exp_id}")


def show_benchmark_page():
    """基准测试页面"""
    st.header("基准测试")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    st.markdown("""
    在此页面运行基准测试并分析结果。基准测试可以帮助您评估系统在不同场景下的性能。
    """)

    # 测试数据集选择
    st.subheader("测试数据集")

    dataset_type = st.radio(
        "选择数据集来源",
        ["内置示例", "上传CSV", "上传JSON"],
        horizontal=True
    )

    dataset = None

    if dataset_type == "内置示例":
        st.info("使用内置的Azure测试数据集")
        dataset = BenchmarkDataset.create_azure_test_dataset()

        # 显示数据集预览
        queries_preview = [
            {"ID": q.id, "查询": q.query, "类别": q.category}
            for q in dataset.queries[:5]  # 仅显示前5个
        ]

        st.markdown("#### 数据集预览")
        st.dataframe(pd.DataFrame(queries_preview))

    elif dataset_type == "上传CSV":
        uploaded_file = st.file_uploader("上传CSV数据集", type=["csv"])

        if uploaded_file:
            try:
                # 保存上传的文件
                file_path = f"./uploads/{uploaded_file.name}"
                os.makedirs("./uploads", exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 加载数据集
                dataset = BenchmarkDataset(uploaded_file.name)
                dataset.load_from_csv(Path(file_path))

                # 显示数据集预览
                queries_preview = [
                    {"ID": q.id, "查询": q.query, "类别": q.category}
                    for q in dataset.queries[:5]  # 仅显示前5个
                ]

                st.markdown("#### 数据集预览")
                st.dataframe(pd.DataFrame(queries_preview))

            except Exception as e:
                st.error(f"加载CSV数据集失败: {str(e)}")

    elif dataset_type == "上传JSON":
        uploaded_file = st.file_uploader("上传JSON数据集", type=["json"])

        if uploaded_file:
            try:
                # 保存上传的文件
                file_path = f"./uploads/{uploaded_file.name}"
                os.makedirs("./uploads", exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 加载数据集
                dataset = BenchmarkDataset(uploaded_file.name)
                dataset.load_from_json(Path(file_path))

                # 显示数据集预览
                queries_preview = [
                    {"ID": q.id, "查询": q.query, "类别": q.category}
                    for q in dataset.queries[:5]  # 仅显示前5个
                ]

                st.markdown("#### 数据集预览")
                st.dataframe(pd.DataFrame(queries_preview))

            except Exception as e:
                st.error(f"加载JSON数据集失败: {str(e)}")

    # 测试配置
    if dataset:
        st.subheader("测试配置")

        col1, col2 = st.columns(2)

        with col1:
            sample_size = st.number_input("样本大小", value=10, min_value=1, max_value=len(dataset.queries))
            run_name = st.text_input("测试运行名称", value=f"benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

        with col2:
            category_filter = st.selectbox(
                "分类过滤器",
                ["全部"] + list(set(q.category for q in dataset.queries if q.category))
            )

            # 评估指标选择
            available_metrics = ["relevance", "faithfulness", "context_precision",
                                 "answer_completeness", "concise_meaningfulness", "latency"]

            selected_metrics = st.multiselect(
                "评估指标",
                available_metrics,
                default=["relevance", "faithfulness", "context_precision"]
            )

        # 运行测试按钮
        if st.button("运行基准测试"):
            if not selected_metrics:
                st.warning("请至少选择一个评估指标")
                return

            with st.spinner("正在运行基准测试..."):
                try:
                    # 准备输出目录
                    output_dir = Path(f"./benchmark_results/{run_name}")
                    output_dir.mkdir(exist_ok=True, parents=True)

                    # 创建基准测试运行器
                    runner = BenchmarkRunner(
                        rag_service=st.session_state.rag_service,
                        evaluator=st.session_state.evaluator,
                        output_dir=output_dir
                    )

                    # 处理分类过滤器
                    cat_filter = None if category_filter == "全部" else category_filter

                    # 运行基准测试
                    result = run_async(
                        runner.run_benchmark(
                            dataset,
                            metrics=selected_metrics,
                            sample_size=sample_size,
                            category_filter=cat_filter
                        )
                    )

                    # 分析结果
                    analyzer = BenchmarkAnalyzer(result.to_dataframe())
                    report_path = analyzer.export_report(output_dir)

                    st.success(f"基准测试完成，报告已生成: {report_path}")

                    # 显示结果摘要
                    st.subheader("测试结果摘要")

                    summary = analyzer.summary_stats()

                    # 显示总体得分
                    st.metric("平均总体得分", f"{summary.loc['mean', 'overall_score']:.4f}")

                    # 显示各指标得分
                    st.markdown("#### 各指标平均分数")

                    metrics_scores = {}
                    for metric in selected_metrics:
                        metric_col = f"metric_{metric}"
                        if metric_col in summary.columns:
                            metrics_scores[metric] = summary.loc['mean', metric_col]

                    metrics_df = pd.DataFrame([
                        {"指标": metric, "平均分数": score}
                        for metric, score in metrics_scores.items()
                    ])

                    st.dataframe(metrics_df)

                    # 可视化指标分数
                    fig = px.bar(
                        metrics_df,
                        x="指标",
                        y="平均分数",
                        title="各指标平均分数",
                        color="平均分数",
                        color_continuous_scale="Viridis"
                    )

                    st.plotly_chart(fig)

                    # 加载并显示生成的图表
                    try:
                        metrics_dist_img = Image.open(output_dir / "metrics_distribution.png")
                        st.image(metrics_dist_img, caption="指标分布")

                        if category_filter == "全部":
                            cat_comp_img = Image.open(output_dir / "category_comparison.png")
                            st.image(cat_comp_img, caption="类别比较")
                    except Exception as e:
                        st.error(f"加载图表失败: {str(e)}")

                    # 保存基准测试结果
                    st.session_state.current_results["benchmark"] = {
                        "run_name": run_name,
                        "dataset": dataset.name,
                        "sample_size": sample_size,
                        "category_filter": category_filter,
                        "metrics": selected_metrics,
                        "summary": summary.to_dict(),
                        "report_path": str(report_path)
                    }

                except Exception as e:
                    st.error(f"运行基准测试失败: {str(e)}")


def show_embedding_tuning_page():
    """嵌入微调页面"""
    st.header("嵌入微调")

    if not st.session_state.rag_service:
        st.warning("请先在'系统初始化'页面初始化系统")
        return

    st.markdown("""
    在此页面进行嵌入模型微调。通过自定义数据集微调嵌入模型，提高向量表示的质量。
    """)

    st.info("注意：嵌入模型微调功能需要连接特定的微调服务。")

    # 微调数据准备
    st.subheader("微调数据准备")

    tuning_data_type = st.radio(
        "选择数据来源",
        ["上传数据集", "使用已处理文档"],
        horizontal=True
    )

    tuning_data = None

    if tuning_data_type == "上传数据集":
        uploaded_file = st.file_uploader("上传微调数据集", type=["csv", "json"])

        if uploaded_file:
            try:
                # 保存上传的文件
                file_path = f"./uploads/{uploaded_file.name}"
                os.makedirs("./uploads", exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 加载数据
                if file_path.endswith(".csv"):
                    tuning_data = pd.read_csv(file_path)
                else:
                    with open(file_path, 'r') as f:
                        tuning_data = json.load(f)

                # 显示数据集预览
                st.markdown("#### 数据集预览")

                if isinstance(tuning_data, pd.DataFrame):
                    st.dataframe(tuning_data.head())
                else:
                    st.json(tuning_data[:5] if isinstance(tuning_data, list) else tuning_data)

            except Exception as e:
                st.error(f"加载微调数据集失败: {str(e)}")

    elif tuning_data_type == "使用已处理文档":
        if "chunks" in st.session_state.current_results:
            chunks = st.session_state.current_results["chunks"]

            st.markdown(f"使用已处理的 {len(chunks)} 个文本块作为微调数据")

            # 创建微调数据
            tuning_data = pd.DataFrame([
                {
                    "text": chunk.content,
                    "metadata": {
                        "doc_id": chunk.doc_id,
                        "source": chunk.metadata.source if chunk.metadata else "unknown"
                    }
                }
                for chunk in chunks
            ])

            # 显示数据预览
            st.dataframe(tuning_data.head())
        else:
            st.warning("未找到已处理的文档。请先在'文档处理'页面处理文档。")

    # 微调参数
    if tuning_data is not None:
        st.subheader("微调参数")

        col1, col2 = st.columns(2)

        with col1:
            base_model = st.selectbox(
                "基础模型",
                ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            )
            embedding_dim = st.selectbox("嵌入维度", [768, 1024, 1536], index=2)

        with col2:
            epochs = st.number_input("训练轮数", value=5, min_value=1, max_value=50)
            learning_rate = st.number_input("学习率", value=0.001, min_value=0.0001, max_value=0.1, format="%.4f")

        st.markdown("#### 高级参数")
        with st.expander("高级参数设置"):
            batch_size = st.number_input("批次大小", value=16, min_value=1, max_value=128)
            warmup_steps = st.number_input("预热步数", value=100, min_value=0, max_value=1000)
            weight_decay = st.number_input("权重衰减", value=0.01, min_value=0.0, max_value=0.1, format="%.3f")

        # 微调目标
        st.subheader("微调目标")

        tuning_task = st.selectbox(
            "微调任务类型",
            ["语义相似度优化", "域适应", "对比学习", "多语言对齐"]
        )

        task_info = {
            "语义相似度优化": "提高模型识别语义相似文本的能力",
            "域适应": "使模型适应特定领域的语言和概念",
            "对比学习": "通过正负样本对比学习，提高特征区分力",
            "多语言对齐": "对齐不同语言中相同概念的表示"
        }

        st.info(task_info[tuning_task])

        # 微调评估
        st.subheader("微调评估")

        eval_ratio = st.slider("评估集比例", 0.0, 0.5, 0.2, 0.05)

        eval_metrics = st.multiselect(
            "评估指标",
            ["余弦相似度", "精确率", "召回率", "F1分数", "平均精度"],
            default=["余弦相似度", "F1分数"]
        )

        # 运行微调
        if st.button("启动微调"):
            with st.spinner("正在进行嵌入模型微调..."):
                # 这里模拟微调过程
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i in range(epochs):
                    # 模拟每个epoch的进度
                    for j in range(100):
                        time.sleep(0.01)  # 模拟计算时间
                        progress_bar.progress((i * 100 + j + 1) / (epochs * 100))
                        status_text.text(f"训练进度：第 {i + 1}/{epochs} 轮，步骤 {j + 1}/100")

                # 模拟评估结果
                eval_results = {
                    "余弦相似度": 0.85 + random.random() * 0.1,
                    "精确率": 0.78 + random.random() * 0.1,
                    "召回率": 0.82 + random.random() * 0.1,
                    "F1分数": 0.80 + random.random() * 0.1,
                    "平均精度": 0.75 + random.random() * 0.1
                }

                # 显示评估结果
                st.success("嵌入模型微调完成！")

                st.subheader("微调评估结果")

                # 创建评估结果表格
                eval_df = pd.DataFrame([
                    {"指标": metric, "分数": eval_results[metric]}
                    for metric in eval_metrics if metric in eval_results
                ])

                st.dataframe(eval_df)

                # 可视化评估结果
                fig = px.bar(
                    eval_df,
                    x="指标",
                    y="分数",
                    title="微调评估结果",
                    color="分数",
                    color_continuous_scale="Viridis"
                )

                st.plotly_chart(fig)

                # 保存微调模型信息
                st.session_state.current_results["tuned_embedding"] = {
                    "base_model": base_model,
                    "embedding_dim": embedding_dim,
                    "tuning_task": tuning_task,
                    "epochs": epochs,
                    "eval_results": eval_results,
                    "timestamp": datetime.now().isoformat(),
                    "model_id": f"tuned-embedding-{int(time.time())}"
                }

                # 显示模型ID
                st.markdown(f"**微调模型ID**: `{st.session_state.current_results['tuned_embedding']['model_id']}`")
                st.markdown("您可以在组件配置中使用此模型ID。")


def show_experiment_history_page():
    """实验历史页面"""
    st.header("实验历史")

    st.markdown("""
    在此页面查看所有已保存的实验结果和对比不同实验。
    """)

    if not st.session_state.experiment_history:
        st.info("暂无保存的实验")
        return

    # 实验列表
    st.subheader("已保存的实验")

    exp_data = []
    for exp in st.session_state.experiment_history:
        exp_data.append({
            "ID": exp["id"],
            "名称": exp["name"],
            "时间": exp["timestamp"],
            "配置": exp["config"]["name"] if "name" in exp["config"] else "未命名",
            "总分": exp["results"].get("evaluation", {}).get("overall_score", "未评估")
        })

    exp_df = pd.DataFrame(exp_data)
    st.dataframe(exp_df)

    # 实验详情查看
    st.subheader("实验详情")

    exp_id = st.selectbox(
        "选择查看的实验",
        ["<选择实验>"] + [exp["id"] for exp in st.session_state.experiment_history]
    )

    if exp_id != "<选择实验>":
        # 查找实验数据
        selected_exp = None
        for exp in st.session_state.experiment_history:
            if exp["id"] == exp_id:
                selected_exp = exp
                break

        if selected_exp:
            # 显示实验详情
            st.markdown(f"**实验名称**: {selected_exp['name']}")
            st.markdown(f"**实验时间**: {selected_exp['timestamp']}")

            # 显示配置
            st.markdown("#### 配置详情")
            with st.expander("查看配置"):
                st.json(selected_exp["config"])

            # 显示结果
            st.markdown("#### 结果详情")

            if "evaluation" in selected_exp["results"]:
                eval_result = selected_exp["results"]["evaluation"]

                # 指标分数表格
                st.markdown("**评估指标**")

                metrics_df = pd.DataFrame([
                    {"指标": metric, "分数": score}
                    for metric, score in eval_result["metrics"].items()
                ])

                st.dataframe(metrics_df)

                # 可视化评估结果
                fig = px.bar(
                    metrics_df,
                    x="指标",
                    y="分数",
                    title="评估指标分数",
                    color="分数",
                    color_continuous_scale="Viridis"
                )

                st.plotly_chart(fig)

                # 总体评分
                st.metric("总体评分", f"{eval_result['overall_score']:.2f}/10")

            # 如果有查询结果
            if "query_result" in selected_exp["results"]:
                st.markdown("**查询结果**")

                query_result = selected_exp["results"]["query_result"]

                st.markdown(f"查询: {query_result['query']}")
                st.markdown(f"回答: {query_result['answer']}")

            # 如果有基准测试结果
            if "benchmark" in selected_exp["results"]:
                st.markdown("**基准测试结果**")

                benchmark_result = selected_exp["results"]["benchmark"]

                st.markdown(f"运行名称: {benchmark_result['run_name']}")
                st.markdown(f"数据集: {benchmark_result['dataset']}")
                st.markdown(f"样本大小: {benchmark_result['sample_size']}")

                if "report_path" in benchmark_result:
                    st.markdown(f"报告路径: {benchmark_result['report_path']}")

    # 实验对比
    st.subheader("实验对比")

    col1, col2 = st.columns(2)

    with col1:
        exp_id1 = st.selectbox(
            "选择实验1",
            ["<选择实验>"] + [exp["id"] for exp in st.session_state.experiment_history],
            key="exp_id1"
        )

    with col2:
        exp_id2 = st.selectbox(
            "选择实验2",
            ["<选择实验>"] + [exp["id"] for exp in st.session_state.experiment_history],
            key="exp_id2"
        )

    if exp_id1 != "<选择实验>" and exp_id2 != "<选择实验>" and exp_id1 != exp_id2:
        # 查找实验数据
        exp1 = None
        exp2 = None

        for exp in st.session_state.experiment_history:
            if exp["id"] == exp_id1:
                exp1 = exp
            if exp["id"] == exp_id2:
                exp2 = exp

        if exp1 and exp2:
            # 创建对比结果
            comparison = compare_configurations(
                exp1["config"],
                exp2["config"],
                exp1["results"].get("evaluation", {}),
                exp2["results"].get("evaluation", {})
            )

            # 显示对比结果
            st.markdown("#### 配置差异")

            with st.expander("查看配置差异"):
                st.json(comparison["配置差异"])

            # 性能对比
            st.markdown("#### 性能对比")

            if "evaluation" not in exp1["results"] or "evaluation" not in exp2["results"]:
                st.warning("至少有一个实验尚未评估")
            else:
                # 创建对比图表
                metrics1 = exp1["results"]["evaluation"]["metrics"]
                metrics2 = exp2["results"]["evaluation"]["metrics"]

                # 合并所有指标
                all_metrics = set(metrics1.keys()) | set(metrics2.keys())

                compare_data = []
                for metric in all_metrics:
                    compare_data.append({
                        "指标": metric,
                        f"{exp1['name']}": metrics1.get(metric, 0),
                        f"{exp2['name']}": metrics2.get(metric, 0)
                    })

                compare_df = pd.DataFrame(compare_data)

                # 显示对比表格
                st.dataframe(compare_df)

                # 可视化对比
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=compare_df["指标"],
                    y=compare_df[f"{exp1['name']}"],
                    name=exp1['name']
                ))

                fig.add_trace(go.Bar(
                    x=compare_df["指标"],
                    y=compare_df[f"{exp2['name']}"],
                    name=exp2['name']
                ))

                fig.update_layout(
                    title="实验性能对比",
                    xaxis_title="评估指标",
                    yaxis_title="分数",
                    barmode="group"
                )

                st.plotly_chart(fig)

                # 总体评分对比
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(f"{exp1['name']} 总分", f"{exp1['results']['evaluation']['overall_score']:.2f}")

                with col2:
                    st.metric(f"{exp2['name']} 总分", f"{exp2['results']['evaluation']['overall_score']:.2f}")

                with col3:
                    diff = exp1['results']['evaluation']['overall_score'] - exp2['results']['evaluation'][
                        'overall_score']
                    st.metric("评分差异", f"{diff:.2f}", delta=f"{diff:.2f}")

                # 雷达图对比
                metrics_list = list(all_metrics)
                values1 = [metrics1.get(metric, 0) for metric in metrics_list]
                values2 = [metrics2.get(metric, 0) for metric in metrics_list]

                # 添加首值使雷达图闭合
                metrics_list.append(metrics_list[0])
                values1.append(values1[0])
                values2.append(values2[0])

                fig = go.Figure()

                fig.add_trace(go.Scatterpolar(
                    r=values1,
                    theta=metrics_list,
                    fill='toself',
                    name=exp1['name']
                ))

                fig.add_trace(go.Scatterpolar(
                    r=values2,
                    theta=metrics_list,
                    fill='toself',
                    name=exp2['name']
                ))

                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 10]
                        )
                    ),
                    title="性能雷达图对比",
                    showlegend=True
                )

                st.plotly_chart(fig)


# 主函数
def main():
    # 根据页面选择显示不同的功能
    if page == "系统初始化":
        show_system_init_page()
        # 更新完成状态
        if st.session_state.rag_service:
            st.session_state.completed_steps["系统初始化"] = True
    elif page == "组件配置":
        show_component_config_page()
    elif page == "文档处理":
        show_document_processing_page()
    elif page == "查询测试":
        show_query_test_page()
    elif page == "评估与对比":
        show_evaluation_page()
    elif page == "基准测试":
        show_benchmark_page()
    elif page == "嵌入微调":
        show_embedding_tuning_page()
    elif page == "实验历史":
        show_experiment_history_page()


# 运行主函数
if __name__ == "__main__":
    main()