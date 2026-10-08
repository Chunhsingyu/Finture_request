"""LLM 客户端模块"""

import os
import re
from typing import List, Dict
from anthropic import Anthropic


class LLMClient:
    """LLM 客户端，封装 Anthropic API 调用"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """初始化 LLM 客户端"""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        self.client = Anthropic(
            api_key=api_key,
            base_url=base_url
        )
    
    def _extract_text(self, response) -> str:
        """从响应中提取文本，兼容 ThinkingBlock"""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                text_parts.append(block.text)
        
        if text_parts:
            return "\n".join(text_parts)
        
        block_types = [type(b).__name__ for b in response.content]
        return f"[调试] 未找到文本块，响应类型: {block_types}"
    
    def _fix_latex_format(self, text: str) -> str:
        """修复 LaTeX 格式问题"""
        text = re.sub(r'\\(\w+)\*\{(\\?\w+)\}', r'\\$1_{$2}', text)
        text = re.sub(r'\\_\{([^}]+)\}', r'_{\1}', text)
        text = re.sub(r'\\\((.+?)\\\)', r'$\1$', text)
        text = re.sub(r'\\\[(.+?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
        return text
    
    def generate_answer(self, question: str, contexts: List[str]) -> str:
        """基于上下文生成答案（单论文）"""
        context_text = "\n\n---\n\n".join([f"[段落 {i+1}]\n{ctx}" for i, ctx in enumerate(contexts)])
        
        prompt = f"""基于以下论文段落回答用户问题。

{context_text}

用户问题：{question}

请用中文回答。如果涉及数学公式，请使用标准 LaTeX 格式：
- 行内公式用 $...$ 包裹，例如：$E = mc^2$
- 块级公式用 $$...$$ 包裹
- 下标用 _{{}}，上标用 ^{{}}

如果段落中没有相关信息，请说明。"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            answer = self._extract_text(response)
            return self._fix_latex_format(answer)
            
        except Exception as e:
            return f"API 调用失败：{str(e)}"
    
    def generate_cross_paper_answer(self, question: str, contexts: List[str], metadata: List[Dict]) -> str:
        """基于多篇论文的上下文生成答案"""
        if not contexts:
            return "未找到相关段落，无法回答该问题。"
        
        # 按论文 ID 分组段落
        paper_contexts = {}
        for ctx, meta in zip(contexts, metadata):
            paper_id = meta.get("paper_id", "unknown")
            if paper_id not in paper_contexts:
                paper_contexts[paper_id] = []
            paper_contexts[paper_id].append(ctx)
        
        # 构建多论文上下文，严格限制长度
        context_parts = []
        for paper_id, paragraphs in paper_contexts.items():
            context_parts.append(f"\n\n===== 论文 {paper_id} =====\n")
            # 每篇论文最多取 2 个段落
            for i, para in enumerate(paragraphs[:2], 1):
                # 限制段落长度到 500 字符
                para_text = para[:500] if len(para) > 500 else para
                context_parts.append(f"[论文{paper_id} 段落{i}]\n{para_text}")
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""基于以下多篇论文的段落回答用户问题。如果涉及比较，请明确指出各论文的异同。

{context_text}

用户问题：{question}

请用中文简洁回答（控制在 500 字以内）。如果涉及数学公式，请使用标准 LaTeX 格式：
- 行内公式用 $...$ 包裹
- 块级公式用 $$...$$ 包裹

如果段落中没有相关信息，请说明。"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            answer = self._extract_text(response)
            return self._fix_latex_format(answer)
            
        except Exception as e:
            return f"API 调用失败：{str(e)}"
