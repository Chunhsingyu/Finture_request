"""LLM 调用封装模块"""

import time
from typing import List, Dict

import anthropic


class LLMClient:
    """LLM 客户端，封装 anthropic SDK"""
    
    SYSTEM_PROMPT = """你是一个论文阅读助手。基于提供的论文段落回答用户问题。

要求：
1. 回答要准确、简洁
2. 引用原文时标注来源（段落编号）
3. 如果提供的段落中没有相关信息，请明确说明
4. 不要编造信息"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """初始化客户端
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url
        )
    
    def _extract_text(self, response) -> str:
        """从响应中提取文本，兼容 ThinkingBlock
        
        DeepSeek API 可能返回 ThinkingBlock（思考过程）+ TextBlock（实际回答），
        需要遍历 content blocks 找到有 text 属性的块。
        """
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        
        if text_parts:
            return "\n".join(text_parts)
        
        raise RuntimeError(f"无法从响应中提取文本，content 类型: {[type(b).__name__ for b in response.content]}")
    
    def chat(self, messages: List[Dict], system: str = None, max_tokens: int = 2000) -> str:
        """发送聊天请求
        
        Args:
            messages: [{"role": "user", "content": "..."}, ...]
            system: 系统提示词
            max_tokens: 最大生成 token 数
        
        Returns:
            模型回复文本
        """
        system_prompt = system or self.SYSTEM_PROMPT
        
        # 重试机制
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=messages
                )
                return self._extract_text(response)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"API 调用失败（第 {attempt + 1} 次），{retry_delay} 秒后重试: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise RuntimeError(f"API 调用失败，已重试 {max_retries} 次: {e}")
    
    def generate_answer(self, question: str, contexts: List[str]) -> str:
        """基于上下文生成答案
        
        Args:
            question: 用户问题
            contexts: 检索到的相关段落
        
        Returns:
            生成的答案
        """
        if not contexts:
            return "未找到相关的论文段落，无法回答该问题。"
        
        # 构建上下文文本，标注段落编号
        context_parts = []
        for i, ctx in enumerate(contexts, 1):
            context_parts.append(f"[段落 {i}]\n{ctx}")
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        user_content = f"相关论文段落：\n\n{context_text}\n\n用户问题：{question}"
        
        messages = [{"role": "user", "content": user_content}]
        
        return self.chat(messages, system=self.SYSTEM_PROMPT)
