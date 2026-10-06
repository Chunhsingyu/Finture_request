# 论文阅读助手 方案（含向量库+历史记忆）

## 目标

**半天内完成一个可以跑通的论文阅读问答工具**

核心场景：

1. 输入 PDF 论文
2. 提取文本内容，切分为段落
3. 用 ChromaDB 构建向量索引
4. 针对论文提问，基于 RAG 检索相关段落，生成回答
5. 保存历史记忆（论文列表 + 对话记录）
6. 支持跨论文查询

**明确不做：**

- ❌ React 前端（用命令行）
- ❌ 图表/公式解析
- ❌ OCR（扫描版 PDF）

---

## 技术方案

### 架构

```
PDF 文件 → pdfplumber 解析 → 文本切分 → ChromaDB 向量化
                                          ↓
用户提问 → ChromaDB 检索相关段落 → 构建 prompt → dpsk API → 回答
                                          ↓
                                    SQLite 保存对话记录
```

### 技术栈

- **PDF 解析：** pdfplumber（已安装）
- **向量库：** ChromaDB（轻量级，嵌入式）
- **历史记忆：** SQLite（Python 内置）
- **LLM 调用：** anthropic SDK（兼容 dpsk）
- **语言：** Python
- **界面：** 命令行交互

### 核心流程

1. **PDF 解析 + 向量化**

   - 用 pdfplumber 提取全文
   - 按段落切分（每段 500-1000 字符）
   - 用 ChromaDB 生成 embedding 并存储
   - 在 SQLite 记录论文元信息
2. **RAG 问答模块**

   - 接收用户问题
   - 用 ChromaDB 检索 top-3 相关段落
   - 构建 prompt（系统提示 + 检索到的段落 + 用户问题）
   - 调用 dpsk API 生成回答
   - 在 SQLite 保存对话记录
3. **历史记忆管理**

   - 列出已读论文
   - 查看某篇论文的对话历史
   - 跨论文查询（"我之前读过的关于 XX 的论文"）
4. **命令行交互**

   - 简单的 REPL 循环
   - 支持命令：load、ask、list、history、search、quit

---

## 工作量拆解

| 任务            | 说明                     |
| --------------- | ------------------------ |
| PDF 解析脚本    | 用 pdfplumber，已有      |
| ChromaDB 集成   | 文本切分 + 向量化 + 检索 |
| SQLite 历史记忆 | 论文表 + 对话表          |
| LLM 调用封装    | anthropic SDK            |
| 命令行交互      | REPL + 命令解析          |
| 联调测试        | 用真实论文测试           |

---

## 关键实现细节

### 1. 数据库初始化

```python
import sqlite3
import chromadb
from chromadb.utils import embedding_functions

# SQLite 初始化
def init_db():
    conn = sqlite3.connect('papers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS papers
                 (id INTEGER PRIMARY KEY, filename TEXT, text TEXT, 
                  char_count INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY, paper_id INTEGER, question TEXT, 
                  answer TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(paper_id) REFERENCES papers(id))''')
    conn.commit()
    return conn

# ChromaDB 初始化
def init_chroma():
    client = chromadb.PersistentClient(path="./chroma_db")
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection("papers", embedding_function=default_ef)
    return client, collection
```

### 2. PDF 解析 + 向量化

```python
import pdfplumber
import re

def extract_and_chunk(pdf_path):
    """提取 PDF 文本并切分为段落"""
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
  
    full_text = "\n\n".join(text)
  
    # 按段落切分（简单策略：按双换行符）
    paragraphs = re.split(r'\n\n+', full_text)
  
    # 过滤太短的段落
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 100]
  
    return full_text, paragraphs

def add_paper_to_db(conn, collection, pdf_path):
    """添加论文到数据库"""
    full_text, paragraphs = extract_and_chunk(pdf_path)
  
    # SQLite 记录论文
    c = conn.cursor()
    c.execute("INSERT INTO papers (filename, text, char_count) VALUES (?, ?, ?)",
              (pdf_path, full_text, len(full_text)))
    paper_id = c.lastrowid
    conn.commit()
  
    # ChromaDB 向量化段落
    ids = [f"paper_{paper_id}_para_{i}" for i in range(len(paragraphs))]
    metadatas = [{"paper_id": paper_id, "para_idx": i} for i in range(len(paragraphs))]
  
    collection.add(
        documents=paragraphs,
        metadatas=metadatas,
        ids=ids
    )
  
    print(f"已加载论文：{pdf_path}")
    print(f"总字符数：{len(full_text)}")
    print(f"切分为 {len(paragraphs)} 个段落")
  
    return paper_id
```

### 3. RAG 问答

```python
import anthropic
import os

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)

def retrieve_context(collection, question, paper_id=None, n_results=3):
    """检索相关段落"""
    where_filter = {"paper_id": paper_id} if paper_id else None
  
    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        where=where_filter
    )
  
    return results['documents'][0]

def ask_question(conn, collection, paper_id, question):
    """基于 RAG 回答问题"""
    # 检索相关段落
    contexts = retrieve_context(collection, question, paper_id)
  
    # 构建 prompt
    context_text = "\n\n---\n\n".join(contexts)
  
    response = client.messages.create(
        model="deepseek-v4-pro",
        max_tokens=2000,
        system="你是一个论文阅读助手。基于提供的论文段落回答用户问题。回答要准确、简洁，并引用原文。如果提供的段落中没有相关信息，请说明。",
        messages=[
            {"role": "user", "content": f"相关论文段落：\n\n{context_text}\n\n用户问题：{question}"}
        ]
    )
  
    answer = response.content[0].text
  
    # 保存对话记录
    c = conn.cursor()
    c.execute("INSERT INTO conversations (paper_id, question, answer) VALUES (?, ?, ?)",
              (paper_id, question, answer))
    conn.commit()
  
    return answer, contexts
```

### 4. 历史记忆查询

```python
def list_papers(conn):
    """列出所有已读论文"""
    c = conn.cursor()
    c.execute("SELECT id, filename, char_count, added_at FROM papers ORDER BY added_at DESC")
    papers = c.fetchall()
  
    if not papers:
        print("还没有读过任何论文")
        return
  
    print("\n已读论文列表：")
    for i, (pid, filename, char_count, added_at) in enumerate(papers, 1):
        print(f"{i}. [{pid}] {filename} ({char_count} 字符) - {added_at}")

def show_history(conn, paper_id):
    """显示某篇论文的对话历史"""
    c = conn.cursor()
    c.execute("SELECT question, answer, timestamp FROM conversations WHERE paper_id=? ORDER BY timestamp",
              (paper_id,))
    conversations = c.fetchall()
  
    if not conversations:
        print("这篇论文还没有对话记录")
        return
  
    print(f"\n论文 {paper_id} 的对话历史：")
    for i, (q, a, ts) in enumerate(conversations, 1):
        print(f"\n--- 对话 {i} ({ts}) ---")
        print(f"问：{q}")
        print(f"答：{a[:200]}...")

def search_papers(collection, query, n_results=5):
    """跨论文搜索"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
  
    print(f"\n搜索 '{query}' 的结果：")
    for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
        print(f"\n{i}. 论文 {meta['paper_id']}，段落 {meta['para_idx']}")
        print(f"   {doc[:200]}...")
```

### 5. 命令行交互

```python
def main():
    conn = init_db()
    _, collection = init_chroma()
  
    current_paper_id = None
  
    print("=== 论文阅读助手 ===")
    print("命令：")
    print("  load <pdf_path>  - 加载论文")
    print("  ask <question>   - 提问")
    print("  list             - 列出已读论文")
    print("  history [id]     - 查看对话历史")
    print("  search <query>   - 跨论文搜索")
    print("  switch <id>      - 切换当前论文")
    print("  quit             - 退出")
    print()
  
    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
          
            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
          
            if action == "quit":
                break
          
            elif action == "load":
                if not arg:
                    print("用法：load <pdf_path>")
                    continue
                current_paper_id = add_paper_to_db(conn, collection, arg)
          
            elif action == "ask":
                if not arg:
                    print("用法：ask <question>")
                    continue
                if current_paper_id is None:
                    print("请先加载论文：load <pdf_path>")
                    continue
                answer, contexts = ask_question(conn, collection, current_paper_id, arg)
                print(f"\n回答：{answer}\n")
                print(f"（基于 {len(contexts)} 个相关段落）")
          
            elif action == "list":
                list_papers(conn)
          
            elif action == "history":
                pid = int(arg) if arg else current_paper_id
                if pid is None:
                    print("用法：history [paper_id]")
                    continue
                show_history(conn, pid)
          
            elif action == "search":
                if not arg:
                    print("用法：search <query>")
                    continue
                search_papers(collection, arg)
          
            elif action == "switch":
                current_paper_id = int(arg)
                print(f"已切换到论文 {current_paper_id}")
          
            else:
                print("未知命令")
      
        except Exception as e:
            print(f"错误：{e}")

if __name__ == "__main__":
    main()
```

---

## 依赖安装

```bash
pip install chromadb pdfplumber anthropic
```

---

## 风险点

### 高风险

1. **ChromaDB embedding 质量**

   - 默认的 `all-MiniLM-L6-v2` 对中文支持一般
   - **缓解：** 如果效果差，换用 `paraphrase-multilingual-MiniLM-L12-v2`
2. **论文太长，段落太多**

   - ChromaDB 存储和检索可能变慢
   - **缓解：** 限制每篇论文最多 100 个段落
3. **dpsk API 不兼容**

   - **缓解：** 先写最小测试脚本验证

### 中风险

1. **PDF 解析质量差**

   - 双栏排版可能提取混乱
   - **缓解：** 接受"够用就行"
2. **SQLite 并发问题**

   - 单用户场景问题不大
   - **缓解：** 每次操作后 commit

---

## 测试计划

用 2-3 篇真实论文测试：

1. 加载论文，检查段落切分是否合理
2. 提问测试：
   - "这篇论文的主要贡献是什么？"
   - "用了什么方法？"
   - "实验结果如何？"
3. 跨论文搜索：
   - "attention mechanism"
   - "实验数据集"
4. 历史记忆：
   - 列出论文
   - 查看对话历史

---

## 交付物

1. `paper_reader.py` - 主程序
2. `requirements.txt` - 依赖列表
3. `README.md` - 使用说明
4. 测试记录（用真实论文的问答截图）

---

## 后续迭代（如果时间允许）

- 加一个简单的 Web 界面（Streamlit）
- 支持论文摘要自动生成
- 支持关键信息提取（方法、数据集、结果）
- 支持导出对话记录

---

## 总结

**半天版本的核心思路：**

- 用 ChromaDB 实现轻量级向量检索
- 用 SQLite 实现历史记忆
- 用 RAG 提升问答质量
- 命令行界面，快速可用

**成功标准：**

- 能解析 PDF 并切分段落
- 能基于检索结果回答问题
- 能记住历史论文和对话
- 能跨论文搜索

**失败预案：**

- 如果 ChromaDB 太慢 → 改为只存最近 5 篇论文
- 如果 embedding 质量差 → 换用多语言模型
- 如果 PDF 解析太差 → 改为手动复制文本
