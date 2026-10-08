# 论文阅读助手

基于 RAG（检索增强生成）的论文阅读问答工具。输入 PDF 论文，通过语义检索 + LLM 生成回答，支持多轮对话和历史记忆。

## 功能

- **PDF 解析** — 自动提取文本，智能切分为段落
- **语义检索** — ChromaDB 向量数据库，按语义相似度检索相关段落
- **智能问答** — 基于检索结果调用 LLM 生成准确回答，引用原文
- **历史记忆** — SQLite 持久化所有论文和对话记录
- **跨论文搜索** — 在所有已读论文中语义检索
- **双界面** — 命令行（CLI）和 Web 界面（Streamlit）

## 快速开始

### 1. 安装依赖

```bash
cd agent
pip3 install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your-api-key",
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"
  }
}
```

或使用系统环境变量：

```bash
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
```

### 3. 启动

**Web 界面（推荐）：**

```bash
cd agent
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

**命令行界面：**

```bash
cd agent
python3 paper_reader.py
```

## Web 界面使用

1. **上传论文**：在左侧边栏点击"选择 PDF 文件"，上传后点击"加载论文"
2. **切换论文**：在"已读论文"列表中点击论文名称
3. **提问**：在底部输入框输入问题，按回车发送
4. **查看统计**：左侧边栏底部显示论文数量和向量段落数

## 命令行界面使用

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

## 项目结构

```
.
├── README.md                  # 本文件
├── JOURNAL.md                 # 学习与开发记录
├── target/                    # 论文缓存目录（PDF 文件）
├── doc/                       # 方案文档
│   ├── DEVELOPMENT_PLAN.md
│   └── plan/
│       └── paper-reader-mvp.md
└── agent/                     # 核心代码
    ├── app.py                 # Web 界面（Streamlit）
    ├── paper_reader.py        # 命令行界面
    ├── config.py              # 配置管理
    ├── pdf_parser.py          # PDF 解析模块
    ├── vector_store.py        # 向量存储（ChromaDB）
    ├── memory_store.py        # 历史记忆（SQLite）
    ├── llm_client.py          # LLM 调用封装
    ├── rag_engine.py          # RAG 检索引擎
    ├── cli.py                 # 命令行交互
    ├── requirements.txt       # 依赖列表
    └── data/                  # 数据存储（运行时生成）
        ├── papers.db          # SQLite 数据库
        └── chroma_db/         # ChromaDB 向量数据
```

## 技术栈

- **PDF 解析：** pdfplumber
- **向量数据库：** ChromaDB（嵌入式，默认 embedding: all-MiniLM-L6-v2）
- **关系数据库：** SQLite
- **LLM 调用：** anthropic SDK（兼容 DeepSeek）
- **Web 界面：** Streamlit
- **语言：** Python 3.9+

## 架构

```
PDF 文件 → pdfplumber 解析 → 文本切分 → ChromaDB 向量化
                                          ↓
用户提问 → ChromaDB 检索相关段落 → 构建 prompt → LLM API → 回答
                                          ↓
                                    SQLite 保存对话记录
```

## 已知限制

- 不支持扫描版 PDF（需要 OCR）
- 双栏排版可能提取混乱
- 默认 embedding 模型对中文支持一般
- 单用户设计，不支持多用户并发
