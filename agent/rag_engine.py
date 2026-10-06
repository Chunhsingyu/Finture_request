"""RAG 检索引擎模块"""

from typing import List, Dict, Optional

from vector_store import VectorStore
from llm_client import LLMClient


class RAGEngine:
    """RAG 引擎，整合向量检索和 LLM 生成"""
    
    def __init__(self, vector_store: VectorStore, llm_client: LLMClient, top_k: int = 3):
        """初始化 RAG 引擎
        
        Args:
            vector_store: 向量存储实例
            llm_client: LLM 客户端实例
            top_k: 检索返回数量
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.top_k = top_k
    
    def query(self, question: str, paper_id: Optional[int] = None) -> Dict:
        """执行 RAG 查询
        
        Args:
            question: 用户问题
            paper_id: 限定论文 ID（可选）
        
        Returns:
            {
                "answer": "生成的答案",
                "contexts": ["段落1", "段落2", ...],
                "metadata": [{"paper_id": 1, "chunk_idx": 0, "score": 0.85}, ...]
            }
        """
        # 1. 检索相关段落
        search_results = self.vector_store.search(
            query=question,
            paper_id=paper_id,
            top_k=self.top_k
        )
        
        if not search_results:
            return {
                "answer": "未找到相关的论文段落，无法回答该问题。",
                "contexts": [],
                "metadata": []
            }
        
        # 2. 提取上下文和元数据
        contexts = [r["text"] for r in search_results]
        metadata = [
            {
                "paper_id": r["paper_id"],
                "chunk_idx": r["chunk_idx"],
                "score": r["score"]
            }
            for r in search_results
        ]
        
        # 3. 生成答案
        answer = self.llm_client.generate_answer(question, contexts)
        
        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata
        }
    
    def search(self, query: str, paper_id: Optional[int] = None, top_k: int = 5) -> List[Dict]:
        """仅执行检索，不生成答案
        
        Args:
            query: 查询文本
            paper_id: 限定论文 ID（可选）
            top_k: 返回数量
        
        Returns:
            [{"text": "...", "paper_id": 1, "chunk_idx": 0, "score": 0.85}, ...]
        """
        return self.vector_store.search(
            query=query,
            paper_id=paper_id,
            top_k=top_k
        )
