"""历史记忆模块 - SQLite 管理"""

import json
import sqlite3
from typing import List, Dict, Optional
from pathlib import Path


class MemoryStore:
    """历史记忆管理器，使用 SQLite 存储论文元信息和对话历史"""
    
    def __init__(self, db_path: str):
        """初始化数据库
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                full_text TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                contexts TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_papers_filename ON papers(filename)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_paper_id ON conversations(paper_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)
        ''')
        
        self.conn.commit()
    
    def add_paper(self, filename: str, full_text: str, char_count: int) -> int:
        """添加论文记录
        
        Args:
            filename: 文件名
            full_text: 全文文本
            char_count: 字符数
        
        Returns:
            paper_id
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO papers (filename, full_text, char_count) VALUES (?, ?, ?)",
            (filename, full_text, char_count)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_paper(self, paper_id: int) -> Optional[Dict]:
        """获取论文信息
        
        Args:
            paper_id: 论文 ID
        
        Returns:
            论文信息字典，不存在返回 None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, filename, full_text, char_count, added_at FROM papers WHERE id = ?",
            (paper_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "filename": row[1],
                "full_text": row[2],
                "char_count": row[3],
                "added_at": row[4]
            }
        return None
    
    def list_papers(self, limit: int = 50) -> List[Dict]:
        """列出所有论文
        
        Args:
            limit: 最大返回数量
        
        Returns:
            论文列表
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, filename, char_count, added_at FROM papers ORDER BY added_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "filename": row[1],
                "char_count": row[2],
                "added_at": row[3]
            }
            for row in rows
        ]
    
    def delete_paper(self, paper_id: int):
        """删除论文及其对话记录
        
        Args:
            paper_id: 论文 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        self.conn.commit()
    
    def add_conversation(self, paper_id: int, question: str, answer: str, contexts: List[str]):
        """添加对话记录
        
        Args:
            paper_id: 论文 ID
            question: 问题
            answer: 回答
            contexts: 检索到的上下文段落
        """
        cursor = self.conn.cursor()
        contexts_json = json.dumps(contexts, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO conversations (paper_id, question, answer, contexts) VALUES (?, ?, ?, ?)",
            (paper_id, question, answer, contexts_json)
        )
        self.conn.commit()
    
    def get_conversations(self, paper_id: int) -> List[Dict]:
        """获取论文的对话历史
        
        Args:
            paper_id: 论文 ID
        
        Returns:
            对话列表
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, question, answer, contexts, timestamp FROM conversations WHERE paper_id = ? ORDER BY timestamp",
            (paper_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "contexts": json.loads(row[3]) if row[3] else [],
                "timestamp": row[4]
            }
            for row in rows
        ]
    
    def search_conversations(self, keyword: str) -> List[Dict]:
        """搜索对话记录（关键词匹配）
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的对话列表
        """
        cursor = self.conn.cursor()
        like_pattern = f"%{keyword}%"
        cursor.execute(
            """SELECT c.id, c.paper_id, p.filename, c.question, c.answer, c.timestamp 
               FROM conversations c 
               JOIN papers p ON c.paper_id = p.id 
               WHERE c.question LIKE ? OR c.answer LIKE ? 
               ORDER BY c.timestamp DESC""",
            (like_pattern, like_pattern)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "paper_id": row[1],
                "filename": row[2],
                "question": row[3],
                "answer": row[4],
                "timestamp": row[5]
            }
            for row in rows
        ]
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
