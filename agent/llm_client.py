"""LLM 客户端模块"""

import os
import re
from typing import List, Dict
from anthropic import Anthropic


class LLMClient:
    """LLM 客户端，封装 Anthropic API 调用"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """初始化 LLM 客户端
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
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
        
        # 如果找不到文本，返回调试信息
        block_types = [type(b).__name__ for b in response.content]
        return f"[调试] 未找到文本块，响应类型: {block_types}"
    
    def _fix_latex_format(self, text: str) -> str:
        """修复 LaTeX 格式问题"""
        # 修复常见的格式错误
        # 1. 修复错误的下标格式：\dot{M}*{\rm BH} -> \dot{M}_{\rm BH}
        text = re.sub(r'\\(\w+)\*\{(\\?\w+)\}', r'\\$1_{$2}', text)
        
        # 2. 修复反斜杠转义：\_{\rm BH} -> _{\rm BH}
        text = re.sub(r'\\_\{([^}]+)\}', r'_{\1}', text)
        
        # 3. 确保行内公式用 $ 包裹
        # 查找 \( ... \) 格式并转换为 $ ... $
        text = re.sub(r'\\\((.+?)\\\)', r'$\1$', text)
        
        # 4. 确保块级公式用 $$ 包裹
        # 查找 \[ ... \] 格式并转换为 $$ ... $$
        text = re.sub(r'\\\[(.+?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
        
        return text
    
    def generate_answer(self, question: str, contexts: List[str]) -> str:
        """基于上下文生成答案（单论文）
        
        Args:
            question: 用户问题
            contexts: 检索到的上下文段落列表
        
        Returns:
            生成的答案
        """
        context_text = "\n\n---\n\n".join([f"[段落 {i+1}]\n{ctx}" for i, ctx in enumerate(contexts)])
        
        prompt = f"""基于以下论文段落回答用户问题。

{context_text}

用户问题：{question}

请用中文回答。如果涉及数学公式，请使用标准 LaTeX 格式：
- 行内公式用 $...$ 包裹，例如：$E = mc^2$
- 块级公式用 $$...$$ 包裹，例如：$$\dot{{M}}_{{\rm BH}} = \dot{{M}}_{{\rm BH,inf}} - \dot{{M}}_{{\rm BH,wind}}$$
- 下标用 _{{}}，上标用 ^{{}}
- 避免使用 \( \) 或 \[ \] 格式

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
        """基于多篇论文的上下文生成答案
        
        Args:
            question: 用户问题
            contexts: 检索到的上下文段落列表
            metadata: 元数据列表，包含 paper_id 等信息
        
        Returns:
            生成的答案
        """
        if not contexts:
            return "未找到相关段落，无法回答该问题。"
        
        # 按论文 ID 分组段落
        paper_contexts = {}
        for ctx, meta in zip(contexts, metadata):
            paper_id = meta.get("paper_id", "unknown")
            if paper_id not in paper_contexts:
                paper_contexts[paper_id] = []
            paper_contexts[paper_id].append(ctx)
        
        # 构建多论文上下文，限制每篇论文的段落数量
        context_parts = []
        for paper_id, paragraphs in paper_contexts.items():
            context_parts.append(f"\n\n===== 论文 {paper_id} =====\n")
            # 每篇论文最多取 3 个段落
            for i, para in enumerate(paragraphs[:3], 1):
                # 限制段落长度
                para_text = para[:1000] if len(para) > 1000 else para
                context_parts.append(f"[论文{paper_id} 段落{i}]\n{para_text}")
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""基于以下多篇论文的段落回答用户问题。如果涉及比较，请明确指出各论文的异同。

{context_text}

用户问题：{question}

请用中文回答。如果涉及数学公式，请使用标准 LaTeX 格式：
- 行内公式用 $...$ 包裹，例如：$E = mc^2$
- 块级公式用 $$...$$ 包裹
- 下标用 _{{}}，上标用 ^{{}}
- 避免使用 \( \) 或 \[ \] 格式

如果段落中没有相关信息，请说明。"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,  # 增加 max_tokens
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            answer = self._extract_text(response)
            return self._fix_latex_format(answer)
            
        except Exception as e:
            return f"API 调用失败：{str(e)}"
