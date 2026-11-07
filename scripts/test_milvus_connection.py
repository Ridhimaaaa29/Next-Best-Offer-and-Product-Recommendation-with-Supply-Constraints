import os

from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

uri = os.getenv("MILVUS_URI")
token = os.getenv("MILVUS_TOKEN")

if not uri:
    raise ValueError("MILVUS_URI is not set in .env")

if not token:
    raise ValueError("MILVUS_TOKEN is not set in .env")

client = MilvusClient(
    uri=uri,
    token=token,
)

print("Milvus connection successful!")
print("Existing collections:", client.list_collections())