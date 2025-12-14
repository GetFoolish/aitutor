import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()


def get_query_embedding(text: str) -> list:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    result = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[text],
        parameters={"input_type": "query"}
    )
    return result[0]["values"]


def get_embeddings_batch(texts: list) -> list:
    if not texts:
        return []
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    result = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=texts,
        parameters={"input_type": "passage"}
    )
    return [item["values"] for item in result]

