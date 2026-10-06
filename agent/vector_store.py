"""向量存储模块 - ChromaDB 管理"""

from typing import List, Dict, Optional

import chromadb
from chromadb.utils import embedding_functions


class VectorStore:
    """向量存储管理器，使用 ChromaDB 进行文本向量化和语义检索"""
    
    def __init__(self, chroma_path: str, collection_name: str = "papers"):
        """初始化向量存储
        
        Args:
            chroma_path: ChromaDB 持久化路径
            collection_name: 集合名称
        """
        self.client = chromadb.PersistentClient(path=chroma_path)
        
        # 使用默认 embedding 函数（all-MiniLM-L6-v2）
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
    
    def add_paper(self, paper_id: int, chunks: List[str], metadata: Optional[Dict] = None):
        """添加论文段落到向量库
        
        Args:
            paper_id: 论文 ID
            chunks: 段落文本列表
            metadata: 额外元数据（可选）
        """
        if not chunks:
            return
        
        ids = [f"paper_{paper_id}_para_{i}" for i in range(len(chunks))]
        
        metadatas = []
        for i in range(len(chunks)):
            meta = {
                "paper_id": paper_id,
                "chunk_idx": i,
            }
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)
        
        # ChromaDB 有批量添加限制，分批处理
        batch_size = 100
        for start in range(0, len(chunks), batch_size):
            end = min(start + batch_size, len(chunks))
            self.collection.add(
                documents=chunks[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end]
            )
    
    def search(self, query: str, paper_id: Optional[int] = None, top_k: int = 3) -> List[Dict]:
        """语义检索
        
        Args:
            query: 查询文本
            paper_id: 限定论文 ID（可选，为 None 时全局检索）
            top_k: 返回数量
        
        Returns:
            [{"text": "...", "paper_id": 1, "chunk_idx": 0, "score": 0.85}, ...]
        """
        where_filter = None
        if paper_id is not None:
            where_filter = {"paper_id": paper_id}
        
        # 确保 top_k 不超过实际数据量
        actual_count = self.collection.count()
        if actual_count == 0:
            return []
        
        effective_top_k = min(top_k, actual_count)
        
        results = self.collection.query(
            query_texts=[query],
            n_results=effective_top_k,
            where=where_filter
        )
        
        output = []
        if results and results['documents'] and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
            distances = results['distances'][0] if results['distances'] else [0] * len(documents)
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                # ChromaDB 返回的是距离，转换为相似度分数（越小越相似）
                score = 1.0 / (1.0 + dist)
                output.append({
                    "text": doc,
                    "paper_id": meta.get("paper_id"),
                    "chunk_idx": meta.get("chunk_idx"),
                    "score": score
                })
        
        return output
    
    def delete_paper(self, paper_id: int):
        """删除论文的所有向量
        
        Args:
            paper_id: 论文 ID
        """
        # 获取该论文的所有 ID
        results = self.collection.get(
            where={"paper_id": paper_id}
        )
        
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
    
    def get_stats(self) -> Dict:
        """获取统计信息
        
        Returns:
            {"total_papers": 5, "total_chunks": 150}
        """
        total_chunks = self.collection.count()
        
        # 统计不同论文数量
        all_data = self.collection.get()
        paper_ids = set()
        if all_data and all_data['metadatas']:
            for meta in all_data['metadatas']:
                if "paper_id" in meta:
                    paper_ids.add(meta["paper_id"])
        
        return {
            "total_papers": len(paper_ids),
            "total_chunks": total_chunks
        }
