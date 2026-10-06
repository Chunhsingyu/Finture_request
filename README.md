# 论文阅读助手

基于 RAG（检索增强生成）的论文阅读问答工具。输入 PDF 论文，通过语义检索 + LLM 生成回答，支持多轮对话和历史记忆。

## 功能

- **PDF 解析** — 自动提取文本，智能切分为段落
- **语义检索** — ChromaDB 向量数据库，按语义相似度检索相关段落
- **智能问答** — 基于检索结果调用 LLM 生成准确回答，引用原文
- **历史记忆** — SQLite 持久化所有论文和对话记录
- **跨论文搜索** — 在所有已读论文中语义检索
- **命令行交互** — 简洁的 REPL 界面

## 快速开始

### 安装依赖

```bash
cd agent
pip3 install -r requirements.txt
```

### 配置环境变量

```bash
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
```

### 运行

```bash
cd agent
python3 paper_reader.py
```

## 论文缓存

所有论文 PDF 文件统一存放在 `target/` 目录（相对于项目根目录）。

**加载论文时：**
- 可以直接输入文件名（如 `load paper.pdf`），程序会自动从缓存目录查找
- 也可以使用相对路径或绝对路径

**查看缓存目录：**
- 使用 `list-cache` 命令列出缓存目录中的所有论文

**默认缓存路径：** `../target`（相对于 `agent/` 目录）

如需修改缓存路径，可在 `agent/config.json` 中配置：

```json
{
  "paper_cache_path": "/your/custom/path"
}
```

## 使用示例

```
=== 论文阅读助手 ===

论文缓存目录：/Users/chenxingyu2/Projects/ft_task/target

> list-cache
缓存目录中的论文：
  1. 2412.19437v2.pdf (1.8 MB)
  2. 2501.12948v2.pdf (4.8 MB)
  3. llama2024llama3.pdf (9.4 MB)

> load 2412.19437v2.pdf
正在解析：/Users/chenxingyu2/Projects/ft_task/target/2412.19437v2.pdf
已加载论文：2412.19437v2.pdf
论文 ID：1
页数：10
总字符数：50000
切分为 45 个段落

> ask 这篇论文的主要贡献是什么？
正在思考...

回答：这篇论文的主要贡献包括...（基于 3 个相关段落）

> list

已读论文列表：
  [1] 2412.19437v2.pdf (50000 字符) - 2026-10-06 12:00:00 ← 当前

> search attention mechanism

搜索 'attention mechanism' 的结果：

  1. 论文 1，段落 5 (相似度: 0.85)
     The attention mechanism is...

> history
论文 [1] 2412.19437v2.pdf 的对话历史：

--- 对话 1 (2026-10-06 12:05:00) ---
问：这篇论文的主要贡献是什么？
答：这篇论文的主要贡献包括...

> quit
再见！
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `load <pdf_path>` | 加载 PDF 论文（支持文件名或路径，自动从缓存目录查找） |
| `list-cache` | 列出缓存目录中的论文 |
| `ask <question>` | 针对当前论文提问 |
| `list` | 列出所有已读论文 |
| `history [paper_id]` | 查看对话历史（默认当前论文） |
| `search <query>` | 跨论文语义搜索 |
| `switch <paper_id>` | 切换当前论文 |
| `delete <paper_id>` | 删除论文 |
| `stats` | 显示统计信息 |
| `help` | 显示帮助 |
| `quit` | 退出 |

## 项目结构

```
.
├── README.md                  # 本文件
├── target/                    # 论文缓存目录（PDF 文件）
├── doc/
│   └── plan/                  # 方案文档
│       └── paper-reader-mvp.md
└── agent/                     # 核心代码
    ├── paper_reader.py        # 主程序入口
    ├── config.py              # 配置管理
    ├── pdf_parser.py          # PDF 解析模块
    ├── vector_store.py        # 向量存储（ChromaDB）
    ├── memory_store.py        # 历史记忆（SQLite）
    ├── llm_client.py          # LLM 调用封装
    ├── rag_engine.py          # RAG 检索引擎
    ├── cli.py                 # 命令行交互
    ├── requirements.txt       # 依赖列表
    ├── DEVELOPMENT_PLAN.md    # 开发方案
    ├── SELF_CHECK.md          # 代码自检报告
    └── data/                  # 数据存储（运行时生成）
        ├── papers.db          # SQLite 数据库
        └── chroma_db/         # ChromaDB 向量数据
```

## 技术栈

- **PDF 解析：** pdfplumber
- **向量数据库：** ChromaDB（嵌入式，默认 embedding: all-MiniLM-L6-v2）
- **关系数据库：** SQLite
- **LLM 调用：** anthropic SDK（兼容 dpsk）
- **语言：** Python 3.9+

## 架构

```
PDF 文件 → pdfplumber 解析 → 文本切分 → ChromaDB 向量化
                                          ↓
用户提问 → ChromaDB 检索相关段落 → 构建 prompt → dpsk API → 回答
                                          ↓
                                    SQLite 保存对话记录
```

## 可选配置

在 `agent/` 目录下创建 `config.json` 自定义配置：

```json
{
  "model_name": "deepseek-v4-pro",
  "db_path": "./data/papers.db",
  "chroma_path": "./data/chroma_db",
  "paper_cache_path": "../target",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "top_k": 3,
  "max_tokens": 2000
}
```

## 已知限制

- 不支持扫描版 PDF（需要 OCR）
- 双栏排版可能提取混乱
- 默认 embedding 模型对中文支持一般
- 单用户设计，不支持多用户并发
