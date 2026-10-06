# 论文阅读助手

基于 RAG（检索增强生成）的论文阅读问答工具，支持 PDF 解析、语义检索、多轮对话和历史记忆。

## 功能特性

- **PDF 解析**：自动提取论文文本内容，智能切分为段落
- **语义检索**：基于 ChromaDB 向量数据库，支持语义相似度检索
- **智能问答**：基于检索结果调用 LLM 生成准确回答
- **历史记忆**：保存所有论文和对话记录，支持跨论文查询
- **命令行界面**：简洁的 REPL 交互，易于使用

## 安装

### 依赖安装

```bash
pip3 install -r requirements.txt
```

### 环境变量配置

```bash
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
```

## 使用方法

### 启动程序

```bash
python3 paper_reader.py
```

### 论文缓存

所有论文 PDF 文件统一存放在 `target/` 目录（相对于项目根目录）。

**加载论文时：**
- 可以直接输入文件名（如 `load paper.pdf`），程序会自动从缓存目录查找
- 也可以使用相对路径或绝对路径

**查看缓存目录：**
- 使用 `list-cache` 命令列出缓存目录中的所有论文

**默认缓存路径：** `../target`（相对于 `agent/` 目录）

如需修改缓存路径，可在 `config.json` 中配置。

### 命令列表

```
load <pdf_path>      加载 PDF 论文（支持文件名或路径，自动从缓存目录查找）
list-cache           列出缓存目录中的论文
ask <question>       针对当前论文提问
list                 列出所有已读论文
history [paper_id]   查看对话历史
search <query>       跨论文语义搜索
switch <paper_id>    切换当前论文
delete <paper_id>    删除论文
stats                显示统计信息
help                 显示帮助
quit                 退出
```

### 使用示例

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

> quit
再见！
```

## 项目结构

```
agent/
├── paper_reader.py      # 主程序入口
├── config.py            # 配置管理
├── pdf_parser.py        # PDF 解析模块
├── vector_store.py      # 向量存储模块（ChromaDB）
├── memory_store.py      # 历史记忆模块（SQLite）
├── llm_client.py        # LLM 调用封装
├── rag_engine.py        # RAG 检索引擎
├── cli.py               # 命令行交互
├── requirements.txt     # 依赖列表
├── README.md            # 使用说明
└── data/                # 数据存储目录
    ├── papers.db        # SQLite 数据库
    └── chroma_db/       # ChromaDB 向量数据
```

## 技术栈

- **PDF 解析**：pdfplumber
- **向量数据库**：ChromaDB
- **关系数据库**：SQLite
- **LLM 调用**：anthropic SDK（兼容 dpsk）
- **语言**：Python 3.9+

## 已知限制

1. 不支持扫描版 PDF（需要 OCR）
2. 双栏排版可能提取混乱
3. 默认 embedding 模型对中文支持一般
4. 单用户设计，不支持多用户并发

## 配置文件（可选）

创建 `config.json` 自定义配置：

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

## 开发计划

详见 `DEVELOPMENT_PLAN.md`
