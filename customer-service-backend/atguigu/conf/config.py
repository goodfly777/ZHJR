from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 指向根目录项的 .env 文件
ENV_FILE = Path(__file__).parents[2] / '.env'

class Settings(BaseSettings):

    # LLM
    # 配置优先（环境变量、.env配置）
    llm_model: str

    # Settings中有，配置中没有，则会读取这里的默认值，如果没有默认值，则会报错
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str

    # 数据库
    database_url: str
    # 该字段在代码中未被使用，但为兼容 pydantic-settings 校验，提供默认值（不依赖 .env 提供）
    database_url_sync: str = ""

    # 金融业务 API（finance-data）配置
    # 注：这些配置项带有默认值，不强制要求写在 .env 中；如需覆盖可自行在 .env 新增（不改动原有项）
    finance_api_base_url: str = "http://127.0.0.1:8000"
    finance_api_prefix: str = "/api/v1"
    finance_channel_code: str = "OPEN_API"
    finance_bearer_token: str = "EMP000006"
    finance_timeout_seconds: float = 5.0
    finance_max_retries: int = 2
    finance_retry_backoff_seconds: float = 0.5

    # 服务器
    app_host: str
    app_port: int

    # 从 .env 文件中读取配置信息
    # 如果读取的是真实的系统环境变量，则不写这句话
    # extra="ignore"： 表示忽略 .env中有，但是Settings中没有的配置项，不会报错
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

settings = Settings()

if __name__ == '__main__':

    print(type(settings.app_port))

    print(Path(__file__).parents[2] / '.env')

    print(settings.llm_base_url)