import os
import uuid
from fastapi import FastAPI, HTTPException
from azure.cosmos import CosmosClient, exceptions

app = FastAPI()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

DB_NAME = "appdb"
CONTAINER_NAME = "jsonfiles"

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
db = client.get_database_client(DB_NAME)
container = db.get_container_client(CONTAINER_NAME)


@app.post("/docs")
def create_doc(payload: dict):
    # мінімальна структура документа
    doc_id = payload.get("id") or str(uuid.uuid4())
    pk = payload.get("pk") or "default"

    doc = {
        "id": doc_id,
        "pk": pk,
        "data": payload,  # зберігаємо весь вхідний JSON як є
    }

    try:
        container.create_item(body=doc)
    except exceptions.CosmosResourceExistsError:
        raise HTTPException(status_code=409, detail="Document with this id already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"id": doc_id, "pk": pk}


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str, pk: str):
    try:
        doc = container.read_item(item=doc_id, partition_key=pk)
        return doc
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")


@app.get("/ping")
def ping():
    return {"status": "ok"}