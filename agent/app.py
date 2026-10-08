"""论文阅读助手 - Streamlit Web UI"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

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


def main():
    st.set_page_config(
        page_title="论文阅读助手",
        page_icon="📚",
        layout="wide"
    )
    
    # 初始化模块
    parser, vector_store, memory_store, rag_engine, config = init_modules()
    
    # 侧边栏：论文管理
    with st.sidebar:
        st.title("📚 论文管理")
        
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
                            # 解析 PDF
                            result = parser.parse(pdf['filepath'])
                            
                            # 存入数据库
                            paper_id = memory_store.add_paper(
                                filename=result["filename"],
                                full_text=result["full_text"],
                                char_count=result["char_count"]
                            )
                            
                            # 存入向量库
                            vector_store.add_paper(
                                paper_id=paper_id,
                                chunks=result["chunks"]
                            )
                            
                            st.success(f"已加载：{result['filename']}")
                            st.info(f"页数：{result['page_count']} | 段落：{len(result['chunks'])}")
                            
                            # 设置当前论文
                            st.session_state.current_paper_id = paper_id
                            
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
                    # 保存临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        # 解析 PDF
                        result = parser.parse(tmp_path)
                        
                        # 存入数据库
                        paper_id = memory_store.add_paper(
                            filename=result["filename"],
                            full_text=result["full_text"],
                            char_count=result["char_count"]
                        )
                        
                        # 存入向量库
                        vector_store.add_paper(
                            paper_id=paper_id,
                            chunks=result["chunks"]
                        )
                        
                        st.success(f"已加载：{result['filename']}")
                        st.info(f"页数：{result['page_count']} | 段落：{len(result['chunks'])}")
                        
                        # 设置当前论文
                        st.session_state.current_paper_id = paper_id
                        
                    except Exception as e:
                        st.error(f"加载失败：{e}")
                    finally:
                        # 清理临时文件
                        os.unlink(tmp_path)
        
        st.divider()
        
        # 已读论文列表
        st.subheader("已读论文")
        papers = memory_store.list_papers()
        
        if not papers:
            st.info("还没有读过任何论文")
        else:
            # 初始化当前论文
            if "current_paper_id" not in st.session_state:
                st.session_state.current_paper_id = papers[0]["id"]
            
            for paper in papers:
                is_current = paper["id"] == st.session_state.current_paper_id
                button_type = "primary" if is_current else "secondary"
                
                if st.button(
                    f"{paper['filename']}",
                    key=f"paper_{paper['id']}",
                    type=button_type,
                    use_container_width=True
                ):
                    st.session_state.current_paper_id = paper["id"]
                    st.session_state.messages = []  # 清空对话历史
                    st.rerun()
        
        st.divider()
        
        # 统计信息
        st.subheader("统计")
        vector_stats = vector_store.get_stats()
        st.metric("论文数量", len(papers))
        st.metric("向量段落", vector_stats["total_chunks"])
    
    # 主界面：问答
    st.title("💬 论文问答")
    
    # 检查是否有当前论文
    if "current_paper_id" not in st.session_state or not papers:
        st.warning("请先从缓存目录加载或上传一篇论文")
        return
    
    current_paper = memory_store.get_paper(st.session_state.current_paper_id)
    st.caption(f"当前论文：{current_paper['filename']}")
    
    # 初始化对话历史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 用户输入
    if prompt := st.chat_input("输入你的问题..."):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 生成回答
        with st.chat_message("assistant"):
            with st.spinner("正在思考..."):
                try:
                    result = rag_engine.query(
                        question=prompt,
                        paper_id=st.session_state.current_paper_id
                    )
                    
                    answer = result["answer"]
                    context_count = len(result["contexts"])
                    
                    # 显示回答
                    st.markdown(answer)
                    st.caption(f"基于 {context_count} 个相关段落")
                    
                    # 保存对话记录
                    memory_store.add_conversation(
                        paper_id=st.session_state.current_paper_id,
                        question=prompt,
                        answer=answer,
                        contexts=result["contexts"]
                    )
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    error_msg = f"提问失败：{e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
