"""配置管理模块"""

import os
import json
from pathlib import Path


class Config:
    """配置管理类，优先从 .env 文件读取，其次从系统环境变量，最后使用默认值"""
    
    DEFAULT_CONFIG = {
        "model_name": "deepseek-v4-pro",
        "db_path": "./data/papers.db",
        "chroma_path": "./data/chroma_db",
        "paper_cache_path": "../target",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 3,
        "max_tokens": 2000
    }
    
    def __init__(self, config_file: str = "config.json"):
        """初始化配置
        
        环境变量加载优先级：
        1. .env 文件（JSON 格式，项目根目录）
        2. 系统环境变量（export）
        
        Args:
            config_file: 配置文件路径（可选）
        """
        # 加载 .env 文件
        self._load_env_file()
        
        self.config = self.DEFAULT_CONFIG.copy()
        
        # 尝试从配置文件加载
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except Exception as e:
                print(f"警告：读取配置文件失败，使用默认配置: {e}")
        
        # 确保数据目录存在
        self._ensure_data_dirs()
    
    def _load_env_file(self):
        """加载 .env 文件（JSON 格式）
        
        查找顺序：
        1. 当前目录（agent/）
        2. 上级目录（项目根目录）
        
        .env 文件格式：
        {
          "env": {
            "ANTHROPIC_AUTH_TOKEN": "xxx",
            "ANTHROPIC_BASE_URL": "xxx"
          }
        }
        """
        env_paths = [
            Path(".env"),           # 当前目录
            Path("../.env"),        # 上级目录（项目根目录）
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        env_data = json.load(f)
                    
                    # 从 "env" 字段提取环境变量
                    if "env" in env_data and isinstance(env_data["env"], dict):
                        for key, value in env_data["env"].items():
                            # 只设置未定义的环境变量（系统环境变量优先）
                            if key not in os.environ:
                                os.environ[key] = str(value)
                    return
                except Exception as e:
                    print(f"警告：读取 .env 文件失败: {e}")
                    continue
    
    def _ensure_data_dirs(self):
        """确保数据目录存在"""
        db_dir = Path(self.config["db_path"]).parent
        chroma_dir = Path(self.config["chroma_path"])
        
        db_dir.mkdir(parents=True, exist_ok=True)
        chroma_dir.mkdir(parents=True, exist_ok=True)
    
    def get_api_key(self) -> str:
        """获取 API 密钥（从环境变量）"""
        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            raise ValueError("未设置环境变量 ANTHROPIC_AUTH_TOKEN\n"
                           "请在项目根目录创建 .env 文件，添加：\n"
                           '{"env": {"ANTHROPIC_AUTH_TOKEN": "your-api-key"}}')
        return api_key
    
    def get_base_url(self) -> str:
        """获取 API 基础 URL（从环境变量）"""
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
        return base_url
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config["model_name"]
    
    def get_db_path(self) -> str:
        """获取 SQLite 数据库路径"""
        return self.config["db_path"]
    
    def get_chroma_path(self) -> str:
        """获取 ChromaDB 存储路径"""
        return self.config["chroma_path"]
    
    def get_paper_cache_path(self) -> str:
        """获取论文缓存路径"""
        return self.config["paper_cache_path"]
    
    def get_chunk_size(self) -> int:
        """获取文本切分大小"""
        return self.config["chunk_size"]
    
    def get_chunk_overlap(self) -> int:
        """获取文本切分重叠"""
        return self.config["chunk_overlap"]
    
    def get_top_k(self) -> int:
        """获取检索返回数量"""
        return self.config["top_k"]
    
    def get_max_tokens(self) -> int:
        """获取最大生成 token 数"""
        return self.config["max_tokens"]
