# 论文阅读助手 - 完整代码开发方案

## 项目概述

基于 RAG（检索增强生成）的论文阅读问答工具，支持 PDF 解析、语义检索、多轮对话和历史记忆。

## 技术栈

- **语言：** Python 3.9+
- **PDF 解析：** pdfplumber
- **向量数据库：** ChromaDB
- **关系数据库：** SQLite（Python 内置）
- **LLM 调用：** anthropic SDK（兼容 dpsk）
- **界面：** 命令行交互（REPL）

## 项目结构

```
agent/
├── paper_reader.py          # 主程序入口
├── config.py                # 配置管理
├── pdf_parser.py            # PDF 解析模块
├── vector_store.py          # 向量存储模块（ChromaDB）
├── memory_store.py          # 历史记忆模块（SQLite）
├── llm_client.py            # LLM 调用封装
├── rag_engine.py            # RAG 检索引擎
├── cli.py                   # 命令行交互
├── requirements.txt         # 依赖列表
├── README.md                # 使用说明
└── tests/                   # 测试目录
    ├── test_pdf_parser.py
    ├── test_vector_store.py
    └── test_rag_engine.py
```

## 模块设计

### 1. config.py - 配置管理

**职责：** 管理所有配置项，包括 API 密钥、数据库路径、模型参数等。

**接口定义：**

```python
class Config:
    def __init__(self, config_file: str = "config.json"):
        """初始化配置，优先从环境变量读取"""

    def get_api_key(self) -> str:
    def get_base_url(self) -> str:
    def get_model_name(self) -> str:
    def get_db_path(self) -> str:
    def get_chroma_path(self) -> str:
    def get_chunk_size(self) -> int:
    def get_top_k(self) -> int:
```

**配置项：**

```json
{
  "api_key": "从环境变量读取",
  "base_url": "从环境变量读取",
  "model_name": "deepseek-v4-pro",
  "db_path": "./data/papers.db",
  "chroma_path": "./data/chroma_db",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "top_k": 3,
  "max_tokens": 2000
}
```

---

### 2. pdf_parser.py - PDF 解析模块

**职责：** 提取 PDF 文本内容，按段落切分，返回结构化数据。

**接口定义：**

```python
class PDFParser:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):

    def extract_text(self, pdf_path: str) -> str:
        """提取 PDF 全文"""

    def extract_pages(self, pdf_path: str) -> List[Dict]:
        """按页提取文本，返回 [{"page": 1, "text": "..."}]"""

    def chunk_text(self, text: str) -> List[str]:
        """将文本切分为段落"""

    def parse(self, pdf_path: str) -> Dict:
        """完整解析，返回 {
            "filename": "xxx.pdf",
            "full_text": "...",
            "chunks": ["段落1", "段落2", ...],
            "page_count": 10,
            "char_count": 50000
        }"""
```

**实现要点：**

1. 使用 pdfplumber 提取文本
2. 按页提取，保留页码信息
3. 文本切分策略：
   - 优先按双换行符切分（段落边界）
   - 如果段落太长（>1000 字符），按句子切分
   - 过滤太短的段落（<100 字符）
4. 处理特殊情况：空页跳过、表格/图表区域标记

---

### 3. vector_store.py - 向量存储模块

**职责：** 管理 ChromaDB，提供文本向量化、存储和检索功能。

**接口定义：**

```python
class VectorStore:
    def __init__(self, chroma_path: str, collection_name: str = "papers"):

    def add_paper(self, paper_id: int, chunks: List[str], metadata: Dict = None):
        """添加论文段落到向量库"""

    def search(self, query: str, paper_id: int = None, top_k: int = 3) -> List[Dict]:
        """语义检索，返回 [{"text": "...", "paper_id": 1, "chunk_idx": 0, "score": 0.85}]"""

    def delete_paper(self, paper_id: int):
        """删除论文的所有向量"""

    def get_stats(self) -> Dict:
        """获取统计信息"""
```

**实现要点：**

1. 使用 ChromaDB 的 PersistentClient
2. 默认 embedding 函数：`all-MiniLM-L6-v2`
3. 元数据结构：`{"paper_id": 1, "chunk_idx": 0, "page": 1, "filename": "xxx.pdf"}`
4. 检索支持全局检索和限定论文检索

---

### 4. memory_store.py - 历史记忆模块

**职责：** 管理 SQLite 数据库，存储论文元信息和对话历史。

**接口定义：**

```python
class MemoryStore:
    def __init__(self, db_path: str):

    def add_paper(self, filename: str, full_text: str, char_count: int) -> int:
        """添加论文记录，返回 paper_id"""

    def get_paper(self, paper_id: int) -> Dict:
    def list_papers(self, limit: int = 50) -> List[Dict]:
    def delete_paper(self, paper_id: int):

    def add_conversation(self, paper_id: int, question: str, answer: str, contexts: List[str]):
    def get_conversations(self, paper_id: int) -> List[Dict]:
    def search_conversations(self, keyword: str) -> List[Dict]:
```

**数据库表结构：**

```sql
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    full_text TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    contexts TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);
```

---

### 5. llm_client.py - LLM 调用封装

**职责：** 封装 anthropic SDK，提供统一的 LLM 调用接口。

**接口定义：**

```python
class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):

    def chat(self, messages: List[Dict], system: str = None, max_tokens: int = 2000) -> str:
        """发送聊天请求"""

    def generate_answer(self, question: str, contexts: List[str]) -> str:
        """基于上下文生成答案"""
```

**Prompt 模板：**

```python
SYSTEM_PROMPT = """你是一个论文阅读助手。基于提供的论文段落回答用户问题。
要求：
1. 回答要准确、简洁
2. 引用原文时标注来源（段落编号）
3. 如果提供的段落中没有相关信息，请明确说明
4. 不要编造信息"""
```

**实现要点：** API 调用失败重试（最多 3 次）、超时处理（30 秒）、网络错误捕获

---

### 6. rag_engine.py - RAG 检索引擎

**职责：** 整合向量检索和 LLM 生成，实现完整的 RAG 流程。

**接口定义：**

```python
class RAGEngine:
    def __init__(self, vector_store: VectorStore, llm_client: LLMClient, top_k: int = 3):

    def query(self, question: str, paper_id: int = None) -> Dict:
        """执行 RAG 查询，返回 {
            "answer": "生成的答案",
            "contexts": ["段落1", "段落2", ...],
            "metadata": [{"paper_id": 1, "chunk_idx": 0, "score": 0.85}]
        }"""

    def search(self, query: str, paper_id: int = None, top_k: int = 5) -> List[Dict]:
        """仅执行检索，不生成答案"""
```

**流程：** 接收问题 → 向量检索 → 构建 prompt → LLM 生成 → 返回答案和上下文

---

### 7. cli.py - 命令行交互

**职责：** 提供命令行界面，解析用户命令，调用后端模块。

**支持的命令：**

```
load <pdf_path>      加载 PDF 论文
ask <question>       针对当前论文提问
list                 列出所有已读论文
history [paper_id]   查看对话历史（默认当前论文）
search <query>       跨论文语义搜索
switch <paper_id>    切换当前论文
delete <paper_id>    删除论文
stats                显示统计信息
help                 显示帮助
quit                 退出
```

**交互示例：**

```
=== 论文阅读助手 ===
> load paper.pdf
已加载论文：paper.pdf
总字符数：50000
切分为 45 个段落

> ask 这篇论文的主要贡献是什么？
回答：这篇论文的主要贡献包括...（基于 3 个相关段落）

> list
已读论文列表：
1. [1] paper.pdf (50000 字符) - 2026-10-06 12:00:00

> search attention mechanism
搜索 'attention mechanism' 的结果：
1. 论文 1，段落 5 (相似度: 0.85)
   The attention mechanism is...

> quit
再见！
```

---

### 8. paper_reader.py - 主程序入口

**职责：** 初始化所有模块，启动 CLI。

```python
def main():
    config = Config()
    parser = PDFParser(chunk_size=config.get_chunk_size())
    vector_store = VectorStore(chroma_path=config.get_chroma_path())
    memory_store = MemoryStore(db_path=config.get_db_path())
    llm_client = LLMClient(api_key=config.get_api_key(), base_url=config.get_base_url(), model=config.get_model_name())
    rag_engine = RAGEngine(vector_store=vector_store, llm_client=llm_client, top_k=config.get_top_k())
    cli = CLI(parser=parser, vector_store=vector_store, memory_store=memory_store, rag_engine=rag_engine)
    cli.run()
```

---

## 数据流

### 论文加载流程

```
用户: load paper.pdf
  → PDFParser.parse("paper.pdf")
  → 返回 {filename, full_text, chunks, page_count, char_count}
  → MemoryStore.add_paper(filename, full_text, char_count) → paper_id
  → VectorStore.add_paper(paper_id, chunks)
  → 完成
```

### 问答流程

```
用户: ask 主要贡献是什么？
  → RAGEngine.query(question, paper_id)
    → VectorStore.search(question, paper_id, top_k=3)
    → 返回相关段落
    → LLMClient.generate_answer(question, contexts)
    → 返回答案
  → MemoryStore.add_conversation(paper_id, question, answer, contexts)
  → 返回答案给用户
```

### 跨论文搜索流程

```
用户: search attention mechanism
  → VectorStore.search("attention mechanism", paper_id=None, top_k=5)
  → 格式化输出
```

---

## 实现步骤

### 阶段 1：基础框架

1. 创建项目结构和 requirements.txt
2. 实现 config.py（环境变量读取）
3. 实现 pdf_parser.py（PDF 提取 + 切分）
4. 实现 memory_store.py（SQLite 增删改查）

### 阶段 2：核心功能

5. 实现 vector_store.py（ChromaDB 向量化 + 检索）
6. 实现 llm_client.py（anthropic SDK 封装）
7. 实现 rag_engine.py（检索 + 生成）

### 阶段 3：用户界面

8. 实现 cli.py（REPL + 命令解析）
9. 实现 paper_reader.py（模块组装 + 启动）

### 阶段 4：测试和优化

10. 编写测试
11. 性能优化和错误处理增强
12. 编写 README.md

---

## 测试策略

### 单元测试

- **test_pdf_parser.py** — PDF 提取、段落切分、边界情况
- **test_vector_store.py** — 向量添加、语义检索、限定检索
- **test_memory_store.py** — 论文增删改查、对话记录
- **test_rag_engine.py** — 完整 RAG 流程、Prompt 构建

### 集成测试

- 端到端：加载论文 → 提问 → 获取答案
- 多论文场景
- 历史记忆验证

### 手动测试

准备 2-3 篇真实论文，测试：
1. 加载单栏/双栏论文，检查段落切分
2. 问答质量（贡献、方法、结果、局限性）
3. 跨论文搜索
4. 边界情况（不存在的 PDF、无关问题、删除正在使用的论文）

---

## 依赖管理

```
pdfplumber>=0.11.0
chromadb>=0.4.0
anthropic>=0.18.0
```

---

## 配置说明

**环境变量：**

```bash
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
```

---

## 已知限制

1. 不支持扫描版 PDF（需要 OCR）
2. 双栏排版可能提取混乱
3. 默认 embedding 模型对中文支持一般
4. 单用户设计，不支持多用户并发

---

## 后续优化方向

1. 支持 OCR、公式和图表提取
2. 混合检索（向量 + 关键词）+ 重排序
3. Web 界面（Streamlit / Gradio）
4. 异步 LLM 调用、批量向量化、缓存机制
