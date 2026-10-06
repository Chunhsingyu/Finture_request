"""PDF 解析模块"""

import re
import os
from typing import List, Dict

import pdfplumber


class PDFParser:
    """PDF 解析器，提取文本并按段落切分"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """初始化解析器
        
        Args:
            chunk_size: 目标段落字符数
            chunk_overlap: 段落间重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text(self, pdf_path: str) -> str:
        """提取 PDF 全文
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            提取的全文文本
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def extract_pages(self, pdf_path: str) -> List[Dict]:
        """按页提取文本
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            [{"page": 1, "text": "..."}, ...]
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    pages.append({"page": i, "text": page_text})
        
        return pages
    
    def chunk_text(self, text: str) -> List[str]:
        """将文本切分为段落
        
        策略：
        1. 优先按双换行符切分（段落边界）
        2. 如果段落太长（>1000 字符），按句子进一步切分
        3. 过滤太短的段落（<100 字符）
        
        Args:
            text: 待切分文本
        
        Returns:
            段落列表
        """
        # 按双换行符切分
        raw_paragraphs = re.split(r'\n\n+', text.strip())
        
        chunks = []
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果段落太长，按句子进一步切分
            if len(para) > 1000:
                sentences = re.split(r'(?<=[.!?。！？])\s+', para)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > self.chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
                
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
            else:
                chunks.append(para)
        
        # 过滤太短的段落
        chunks = [c for c in chunks if len(c.strip()) > 100]
        
        return chunks
    
    def parse(self, pdf_path: str) -> Dict:
        """完整解析 PDF
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            {
                "filename": "xxx.pdf",
                "full_text": "...",
                "chunks": ["段落1", "段落2", ...],
                "page_count": 10,
                "char_count": 50000
            }
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        full_text = self.extract_text(pdf_path)
        chunks = self.chunk_text(full_text)
        
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
        
        return {
            "filename": os.path.basename(pdf_path),
            "full_text": full_text,
            "chunks": chunks,
            "page_count": page_count,
            "char_count": len(full_text)
        }
