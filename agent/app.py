"""论文阅读助手 - Streamlit Web UI"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.manifold import TSNE
import numpy as np

# 确保可以导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from pdf_parser import PDFParser
from vector_store import VectorStore
from memory_store import MemoryStore
from llm_client import LLMClient
from rag_engine import RAGEngine


@st.cache_resource
def init_modules():
    """初始化所有模块（只执行一次）"""
    config = Config()
    
    parser = PDFParser(
        chunk_size=config.get_chunk_size(),
        chunk_overlap=config.get_chunk_overlap()
    )
    
    vector_store = VectorStore(
        chroma_path=config.get_chroma_path(),
        collection_name="papers"
    )
    
    memory_store = MemoryStore(db_path=config.get_db_path())
    
    llm_client = LLMClient(
        api_key=config.get_api_key(),
        base_url=config.get_base_url(),
        model=config.get_model_name()
    )
    
    rag_engine = RAGEngine(
        vector_store=vector_store,
        llm_client=llm_client,
        top_k=config.get_top_k()
    )
    
    return parser, vector_store, memory_store, rag_engine, config


def get_cache_pdfs(cache_path: str):
    """获取缓存目录下的 PDF 文件列表"""
    if not os.path.exists(cache_path):
        return []
    
    pdf_files = []
    for filename in sorted(os.listdir(cache_path)):
        if filename.lower().endswith('.pdf'):
            filepath = os.path.join(cache_path, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            pdf_files.append({
                'filename': filename,
                'filepath': filepath,
                'size_mb': size_mb
            })
    
    return pdf_files


def load_conversations_for_paper(memory_store, paper_id):
    """从 SQLite 加载某篇论文的对话历史到 session_state"""
    conversations = memory_store.get_conversations(paper_id)
    messages = []
    for conv in conversations:
        messages.append({"role": "user", "content": conv["question"]})
        messages.append({"role": "assistant", "content": conv["answer"]})
    st.session_state.messages = messages
    st.session_state.current_paper_id = paper_id


def get_vector_data(vector_store, memory_store):
    """获取向量库数据用于可视化"""
    # 获取所有向量数据
    all_data = vector_store.collection.get(include=['embeddings', 'metadatas', 'documents'])
    
    if all_data['embeddings'] is None or len(all_data['embeddings']) == 0:
        return None
    
    embeddings = np.array(all_data['embeddings'])
    metadatas = all_data['metadatas']
    documents = all_data['documents']
    
    # 获取论文名称映射
    papers = memory_store.list_papers(limit=1000)
    paper_map = {p['id']: p['filename'] for p in papers}
    
    # 构建数据框
    data = []
    for i, (emb, meta, doc) in enumerate(zip(embeddings, metadatas, documents)):
        paper_id = meta.get('paper_id', 'unknown')
        paper_name = paper_map.get(paper_id, f'论文{paper_id}')
        chunk_idx = meta.get('chunk_idx', i)
        
        data.append({
            'paper_id': paper_id,
            'paper_name': paper_name,
            'chunk_idx': chunk_idx,
            'text_preview': doc[:100] + '...' if len(doc) > 100 else doc,
            'embedding': emb
        })
    
    return pd.DataFrame(data)


def visualize_vectors(df):
    """使用 t-SNE 可视化向量"""
    if df is None or len(df) == 0:
        st.warning("没有向量数据可可视化")
        return
    
    st.subheader("向量空间可视化（t-SNE）")
    st.caption("将高维向量降维到 2D 空间，展示论文段落的语义分布")
    
    # 提取嵌入向量
    embeddings = np.array(df['embedding'].tolist())
    
    # t-SNE 降维
    with st.spinner("正在计算 t-SNE..."):
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
        embeddings_2d = tsne.fit_transform(embeddings)
    
    # 添加到数据框
    df['x'] = embeddings_2d[:, 0]
    df['y'] = embeddings_2d[:, 1]
    
    # 创建散点图
    fig = px.scatter(
        df,
        x='x',
        y='y',
        color='paper_name',
        hover_data=['chunk_idx', 'text_preview'],
        title='论文段落向量分布',
        labels={'x': 't-SNE 维度 1', 'y': 't-SNE 维度 2'}
    )
    
    fig.update_traces(marker=dict(size=8, opacity=0.7))
    fig.update_layout(height=600)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 统计信息
    st.subheader("向量统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总段落数", len(df))
    with col2:
        st.metric("论文数量", df['paper_id'].nunique())
    with col3:
        st.metric("向量维度", len(df['embedding'].iloc[0]))
    
    # 每篇论文的段落数
    st.subheader("各论文段落分布")
    paper_stats = df.groupby('paper_name').size().reset_index(name='段落数')
    paper_stats = paper_stats.sort_values('段落数', ascending=False)
    
    fig2 = px.bar(
        paper_stats,
        x='paper_name',
        y='段落数',
        title='各论文段落数量',
        labels={'paper_name': '论文', '段落数': '段落数量'}
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)
    
    # 数据表格
    st.subheader("向量数据详情")
    display_df = df[['paper_name', 'chunk_idx', 'text_preview']].copy()
    display_df.columns = ['论文', '段落索引', '文本预览']
    st.dataframe(display_df, use_container_width=True, height=400)


def main():
    st.set_page_config(
        page_title="论文阅读助手",
        page_icon="📚",
        layout="wide"
    )
    
    # 初始化视图状态
    if "current_view" not in st.session_state:
        st.session_state.current_view = "qa"
    
    # 初始化模块
    parser, vector_store, memory_store, rag_engine, config = init_modules()
    
    # 侧边栏：论文管理
    with st.sidebar:
        st.title("📚 论文管理")
        
        # 视图切换
        st.subheader("功能导航")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💬 问答", use_container_width=True, 
                        type="primary" if st.session_state.current_view == "qa" else "secondary"):
                st.session_state.current_view = "qa"
                st.rerun()
        with col2:
            if st.button("📊 可视化", use_container_width=True,
                        type="primary" if st.session_state.current_view == "viz" else "secondary"):
                st.session_state.current_view = "viz"
                st.rerun()
        
        st.divider()
        
        # 从缓存目录加载
        st.subheader("缓存目录")
        cache_path = config.get_paper_cache_path()
        cache_pdfs = get_cache_pdfs(cache_path)
        
        if cache_pdfs:
            st.caption(f"路径：{os.path.abspath(cache_path)}")
            for pdf in cache_pdfs:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"{pdf['filename']}")
                with col2:
                    st.caption(f"{pdf['size_mb']:.1f}MB")
                
                if st.button("加载", key=f"cache_{pdf['filename']}"):
                    with st.spinner(f"正在加载 {pdf['filename']}..."):
                        try:
                            result = parser.parse(pdf['filepath'])
                            
                            paper_id = memory_store.add_paper(
                                filename=result["filename"],
                                full_text=result["full_text"],
                                char_count=result["char_count"]
                            )
                            
                            vector_store.add_paper(
                                paper_id=paper_id,
                                chunks=result["chunks"]
                            )
                            
                            st.success(f"已加载：{result['filename']}")
                            st.info(f"页数：{result['page_count']} | 段落：{len(result['chunks'])}")
                            
                            load_conversations_for_paper(memory_store, paper_id)
                            
                        except Exception as e:
                            st.error(f"加载失败：{e}")
        else:
            st.info("缓存目录为空")
        
        st.divider()
        
        # 上传论文
        st.subheader("上传论文")
        uploaded_file = st.file_uploader("选择 PDF 文件", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("加载上传的论文", type="primary"):
                with st.spinner("正在解析论文..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        result = parser.parse(tmp_path)
                        
                        paper_id = memory_store.add_paper(
                            filename=result["filename"],
                            full_text=result["full_text"],
                            char_count=result["char_count"]
                        )
                        
                        vector_store.add_paper(
                            paper_id=paper_id,
                            chunks=result["chunks"]
                        )
                        
                        st.success(f"已加载：{result['filename']}")
                        st.info(f"页数：{result['page_count']} | 段落：{len(result['chunks'])}")
                        
                        load_conversations_for_paper(memory_store, paper_id)
                        
                    except Exception as e:
                        st.error(f"加载失败：{e}")
                    finally:
                        os.unlink(tmp_path)
        
        st.divider()
        
        # 已读论文列表
        st.subheader("已读论文")
        papers = memory_store.list_papers()
        
        if not papers:
            st.info("还没有读过任何论文")
        else:
            if "current_paper_id" not in st.session_state:
                load_conversations_for_paper(memory_store, papers[0]["id"])
            
            for paper in papers:
                is_current = paper["id"] == st.session_state.get("current_paper_id")
                button_type = "primary" if is_current else "secondary"
                
                if st.button(
                    f"{paper['filename']}",
                    key=f"paper_{paper['id']}",
                    type=button_type,
                    use_container_width=True
                ):
                    load_conversations_for_paper(memory_store, paper["id"])
                    st.rerun()
        
        st.divider()
        
        # 统计信息
        st.subheader("统计")
        vector_stats = vector_store.get_stats()
        st.metric("论文数量", len(papers))
        st.metric("向量段落", vector_stats["total_chunks"])
    
    # 主界面：根据视图显示不同内容
    if st.session_state.current_view == "qa":
        # 问答视图
        st.title("💬 论文问答")
        
        if "current_paper_id" not in st.session_state or not papers:
            st.warning("请先从缓存目录加载或上传一篇论文")
            return
        
        current_paper = memory_store.get_paper(st.session_state.current_paper_id)
        
        # 问答模式选择
        col1, col2 = st.columns([1, 3])
        with col1:
            query_mode = st.radio(
                "问答模式",
                ["单论文", "跨论文"],
                horizontal=True,
                help="单论文：仅检索当前论文；跨论文：检索所有已读论文"
            )
        with col2:
            if query_mode == "单论文":
                st.caption(f"当前论文：{current_paper['filename']}")
            else:
                st.caption(f"跨论文模式：检索所有 {len(papers)} 篇已读论文")
        
        # 初始化对话历史
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 显示对话历史
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 用户输入
        if prompt := st.chat_input("输入你的问题..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("正在思考..."):
                    try:
                        if query_mode == "单论文":
                            result = rag_engine.query(
                                question=prompt,
                                paper_id=st.session_state.current_paper_id
                            )
                            
                            answer = result["answer"]
                            context_count = len(result["contexts"])
                            source_info = f"基于 {context_count} 个相关段落"
                            
                            memory_store.add_conversation(
                                paper_id=st.session_state.current_paper_id,
                                question=prompt,
                                answer=answer,
                                contexts=result["contexts"]
                            )
                        
                        else:
                            paper_ids = [p["id"] for p in papers]
                            result = rag_engine.query_cross_paper(
                                question=prompt,
                                paper_ids=paper_ids,
                                top_k_per_paper=3
                            )
                            
                            answer = result["answer"]
                            context_count = len(result["contexts"])
                            paper_count = len(set(m["paper_id"] for m in result["metadata"]))
                            source_info = f"基于 {context_count} 个相关段落，来自 {paper_count} 篇论文"
                        
                        st.markdown(answer)
                        st.caption(source_info)
                        
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    except Exception as e:
                        error_msg = f"提问失败：{e}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    elif st.session_state.current_view == "viz":
        # 可视化视图
        st.title("📊 向量库可视化")
        
        papers = memory_store.list_papers()
        if not papers:
            st.warning("请先加载论文")
            return
        
        with st.spinner("正在加载向量数据..."):
            df = get_vector_data(vector_store, memory_store)
        
        if df is not None:
            visualize_vectors(df)
        else:
            st.warning("没有向量数据可可视化")


if __name__ == "__main__":
    main()
