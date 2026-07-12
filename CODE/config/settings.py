import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE: str = os.getenv("AWS_PROFILE", "default")
APP_TITLE: str = os.getenv("APP_TITLE", "AWS Cost Optimizer")
COST_LOOKBACK_DAYS: int = int(os.getenv("COST_LOOKBACK_DAYS", "30"))
API_GATEWAY_URL: str = os.getenv("API_GATEWAY_URL", "")
SUPPORTED_SERVICES = ["EC2", "RDS", "S3", "Lambda", "ECS", "ElastiCache", "NAT Gateway"]