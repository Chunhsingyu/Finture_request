#!/usr/bin/env python3
"""论文阅读助手 - 主程序入口"""

import os
import sys

# 确保可以导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from pdf_parser import PDFParser
from vector_store import VectorStore
from memory_store import MemoryStore
from llm_client import LLMClient
from rag_engine import RAGEngine
from cli import CLI


def main():
    """主函数"""
    try:
        # 1. 加载配置
        config = Config()
        
        # 2. 初始化模块
        parser = PDFParser(
            chunk_size=config.get_chunk_size(),
            chunk_overlap=config.get_chunk_overlap()
        )
        
        vector_store = VectorStore(
            chroma_path=config.get_chroma_path(),
            collection_name="papers"
        )
        
        memory_store = MemoryStore(
            db_path=config.get_db_path()
        )
        
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
        
        # 3. 启动 CLI
        cli = CLI(
            parser=parser,
            vector_store=vector_store,
            memory_store=memory_store,
            rag_engine=rag_engine,
            paper_cache_path=config.get_paper_cache_path()
        )
        
        cli.run()
    
    except KeyboardInterrupt:
        print("\n再见！")
        sys.exit(0)
    except Exception as e:
        print(f"启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
