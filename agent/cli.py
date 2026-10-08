"""命令行交互模块"""

import os
from typing import Optional

from pdf_parser import PDFParser
from vector_store import VectorStore
from memory_store import MemoryStore
from rag_engine import RAGEngine


class CLI:
    """命令行交互界面"""
    
    def __init__(self, parser: PDFParser, vector_store: VectorStore, 
                 memory_store: MemoryStore, rag_engine: RAGEngine,
                 paper_cache_path: str = "../target"):
        """初始化 CLI
        
        Args:
            parser: PDF 解析器
            vector_store: 向量存储
            memory_store: 历史记忆存储
            rag_engine: RAG 引擎
            paper_cache_path: 论文缓存路径
        """
        self.parser = parser
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.rag_engine = rag_engine
        self.paper_cache_path = paper_cache_path
        self.current_paper_id: Optional[int] = None
    
    def run(self):
        """启动 REPL 循环"""
        self._print_welcome()
        
        while True:
            try:
                cmd = input("\n> ").strip()
                if not cmd:
                    continue
                
                self._handle_command(cmd)
            
            except KeyboardInterrupt:
                print("\n使用 'quit' 退出")
            except EOFError:
                print("\n再见！")
                break
            except Exception as e:
                print(f"错误：{e}")
    
    def _print_welcome(self):
        """打印欢迎信息"""
        print("=" * 40)
        print("       论文阅读助手")
        print("=" * 40)
        print()
        print("命令列表：")
        print("  load <pdf_path>      加载 PDF 论文（支持文件名或路径）")
        print("  list-cache           列出缓存目录中的论文")
        print("  ask <question>       针对当前论文提问")
        print("  ask-all <question>   跨论文提问（检索所有已读论文）")
        print("  list                 列出所有已读论文")
        print("  history [paper_id]   查看对话历史")
        print("  search <query>       跨论文语义搜索")
        print("  switch <paper_id>    切换当前论文")
        print("  delete <paper_id>    删除论文")
        print("  stats                显示统计信息")
        print("  help                 显示帮助")
        print("  quit                 退出")
        print()
        print(f"论文缓存目录：{os.path.abspath(self.paper_cache_path)}")
    
    def _resolve_pdf_path(self, pdf_path: str) -> str:
        """解析 PDF 路径
        
        优先级：
        1. 绝对路径直接使用
        2. 相对路径（当前目录）
        3. 从缓存目录查找
        """
        # 如果是绝对路径且存在，直接返回
        if os.path.isabs(pdf_path) and os.path.exists(pdf_path):
            return pdf_path
        
        # 如果在当前目录存在，直接返回
        if os.path.exists(pdf_path):
            return os.path.abspath(pdf_path)
        
        # 从缓存目录查找
        cache_path = os.path.join(self.paper_cache_path, pdf_path)
        if os.path.exists(cache_path):
            return os.path.abspath(cache_path)
        
        # 都不存在，返回原路径（让后续报错）
        return pdf_path
    
    def _handle_command(self, cmd: str):
        """处理用户命令"""
        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if action == "quit" or action == "exit":
            print("再见！")
            return
        
        elif action == "help":
            self._print_welcome()
        
        elif action == "load":
            self._handle_load(arg)
        
        elif action == "list-cache":
            self._handle_list_cache()
        
        elif action == "ask":
            self._handle_ask(arg)
        
        elif action == "ask-all":
            self._handle_ask_all(arg)
        
        elif action == "list":
            self._handle_list()
        
        elif action == "history":
            self._handle_history(arg)
        
        elif action == "search":
            self._handle_search(arg)
        
        elif action == "switch":
            self._handle_switch(arg)
        
        elif action == "delete":
            self._handle_delete(arg)
        
        elif action == "stats":
            self._handle_stats()
        
        else:
            print(f"未知命令：{action}")
            print("输入 'help' 查看帮助")
    
    def _handle_load(self, pdf_path: str):
        """处理 load 命令"""
        if not pdf_path:
            print("用法：load <pdf_path>")
            print("提示：可以直接输入文件名，会从缓存目录查找")
            return
        
        pdf_path = pdf_path.strip()
        
        # 解析路径
        resolved_path = self._resolve_pdf_path(pdf_path)
        
        if not os.path.exists(resolved_path):
            print(f"文件不存在：{pdf_path}")
            print(f"缓存目录：{os.path.abspath(self.paper_cache_path)}")
            print("提示：使用 'list-cache' 查看缓存目录中的论文")
            return
        
        try:
            print(f"正在解析：{resolved_path}")
            
            # 1. 解析 PDF
            result = self.parser.parse(resolved_path)
            
            # 2. 存入 SQLite
            paper_id = self.memory_store.add_paper(
                filename=result["filename"],
                full_text=result["full_text"],
                char_count=result["char_count"]
            )
            
            # 3. 存入 ChromaDB
            self.vector_store.add_paper(
                paper_id=paper_id,
                chunks=result["chunks"]
            )
            
            self.current_paper_id = paper_id
            
            print(f"已加载论文：{result['filename']}")
            print(f"论文 ID：{paper_id}")
            print(f"页数：{result['page_count']}")
            print(f"总字符数：{result['char_count']}")
            print(f"切分为 {len(result['chunks'])} 个段落")
        
        except Exception as e:
            print(f"加载失败：{e}")
    
    def _handle_list_cache(self):
        """处理 list-cache 命令"""
        if not os.path.exists(self.paper_cache_path):
            print(f"缓存目录不存在：{os.path.abspath(self.paper_cache_path)}")
            return
        
        pdf_files = [f for f in os.listdir(self.paper_cache_path) 
                     if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("缓存目录中没有 PDF 文件")
            return
        
        print(f"\n缓存目录中的论文（{os.path.abspath(self.paper_cache_path)}）：")
        for i, filename in enumerate(sorted(pdf_files), 1):
            filepath = os.path.join(self.paper_cache_path, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  {i}. {filename} ({size_mb:.1f} MB)")
    
    def _handle_ask(self, question: str):
        """处理 ask 命令（单论文问答）"""
        if not question:
            print("用法：ask <question>")
            return
        
        if self.current_paper_id is None:
            print("请先加载论文：load <pdf_path>")
            return
        
        try:
            print("正在思考...")
            
            # 执行 RAG 查询
            result = self.rag_engine.query(
                question=question,
                paper_id=self.current_paper_id
            )
            
            # 保存对话记录
            self.memory_store.add_conversation(
                paper_id=self.current_paper_id,
                question=question,
                answer=result["answer"],
                contexts=result["contexts"]
            )
            
            # 输出答案
            print(f"\n回答：{result['answer']}")
            print(f"（基于 {len(result['contexts'])} 个相关段落）")
        
        except Exception as e:
            print(f"提问失败：{e}")
    
    def _handle_ask_all(self, question: str):
        """处理 ask-all 命令（跨论文问答）"""
        if not question:
            print("用法：ask-all <question>")
            return
        
        # 获取所有已读论文
        papers = self.memory_store.list_papers()
        if not papers:
            print("还没有读过任何论文")
            return
        
        paper_ids = [p["id"] for p in papers]
        
        try:
            print(f"正在从 {len(papers)} 篇论文中检索...")
            
            # 执行跨论文 RAG 查询
            result = self.rag_engine.query_cross_paper(
                question=question,
                paper_ids=paper_ids,
                top_k_per_paper=3
            )
            
            # 输出答案
            print(f"\n回答：{result['answer']}")
            print(f"（基于 {len(result['contexts'])} 个相关段落，来自 {len(set(m['paper_id'] for m in result['metadata']))} 篇论文）")
        
        except Exception as e:
            print(f"提问失败：{e}")
    
    def _handle_list(self):
        """处理 list 命令"""
        papers = self.memory_store.list_papers()
        
        if not papers:
            print("还没有读过任何论文")
            return
        
        print("\n已读论文列表：")
        for paper in papers:
            current_mark = " ← 当前" if paper["id"] == self.current_paper_id else ""
            print(f"  [{paper['id']}] {paper['filename']} "
                  f"({paper['char_count']} 字符) - {paper['added_at']}{current_mark}")
    
    def _handle_history(self, arg: str):
        """处理 history 命令"""
        if arg:
            try:
                paper_id = int(arg)
            except ValueError:
                print("用法：history [paper_id]")
                return
        else:
            paper_id = self.current_paper_id
        
        if paper_id is None:
            print("用法：history <paper_id>")
            return
        
        paper = self.memory_store.get_paper(paper_id)
        if not paper:
            print(f"论文不存在：{paper_id}")
            return
        
        conversations = self.memory_store.get_conversations(paper_id)
        
        if not conversations:
            print(f"论文 [{paper_id}] {paper['filename']} 还没有对话记录")
            return
        
        print(f"\n论文 [{paper_id}] {paper['filename']} 的对话历史：")
        for i, conv in enumerate(conversations, 1):
            print(f"\n--- 对话 {i} ({conv['timestamp']}) ---")
            print(f"问：{conv['question']}")
            answer_preview = conv['answer'][:200]
            if len(conv['answer']) > 200:
                answer_preview += "..."
            print(f"答：{answer_preview}")
    
    def _handle_search(self, query: str):
        """处理 search 命令"""
        if not query:
            print("用法：search <query>")
            return
        
        try:
            results = self.rag_engine.search(query=query, top_k=5)
            
            if not results:
                print("未找到相关内容")
                return
            
            print(f"\n搜索 '{query}' 的结果：")
            for i, result in enumerate(results, 1):
                print(f"\n  {i}. 论文 {result['paper_id']}，段落 {result['chunk_idx']} "
                      f"(相似度: {result['score']:.2f})")
                text_preview = result['text'][:200]
                if len(result['text']) > 200:
                    text_preview += "..."
                print(f"     {text_preview}")
        
        except Exception as e:
            print(f"搜索失败：{e}")
    
    def _handle_switch(self, arg: str):
        """处理 switch 命令"""
        if not arg:
            print("用法：switch <paper_id>")
            return
        
        try:
            paper_id = int(arg)
        except ValueError:
            print("用法：switch <paper_id>")
            return
        
        paper = self.memory_store.get_paper(paper_id)
        if not paper:
            print(f"论文不存在：{paper_id}")
            return
        
        self.current_paper_id = paper_id
        print(f"已切换到论文 [{paper_id}] {paper['filename']}")
    
    def _handle_delete(self, arg: str):
        """处理 delete 命令"""
        if not arg:
            print("用法：delete <paper_id>")
            return
        
        try:
            paper_id = int(arg)
        except ValueError:
            print("用法：delete <paper_id>")
            return
        
        paper = self.memory_store.get_paper(paper_id)
        if not paper:
            print(f"论文不存在：{paper_id}")
            return
        
        # 删除向量
        self.vector_store.delete_paper(paper_id)
        
        # 删除数据库记录
        self.memory_store.delete_paper(paper_id)
        
        # 如果删除的是当前论文，清空当前 ID
        if self.current_paper_id == paper_id:
            self.current_paper_id = None
        
        print(f"已删除论文 [{paper_id}] {paper['filename']}")
    
    def _handle_stats(self):
        """处理 stats 命令"""
        # 向量库统计
        vector_stats = self.vector_store.get_stats()
        
        # 数据库统计
        papers = self.memory_store.list_papers(limit=1000)
        total_conversations = 0
        for paper in papers:
            conversations = self.memory_store.get_conversations(paper["id"])
            total_conversations += len(conversations)
        
        print("\n统计信息：")
        print(f"  论文数量：{len(papers)}")
        print(f"  对话数量：{total_conversations}")
        print(f"  向量段落数：{vector_stats['total_chunks']}")
        print(f"  当前论文：{self.current_paper_id or '无'}")
        print(f"  缓存目录：{os.path.abspath(self.paper_cache_path)}")
