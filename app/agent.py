# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google
import vertexai
from google import genai
from google.genai.types import (
    Content,
    FunctionDeclaration,
    LiveConnectConfig,
    Tool,
)
from langchain_google_vertexai import VertexAIEmbeddings

from app.templates import FORMAT_DOCS, SYSTEM_INSTRUCTION
from app.vector_store import get_vector_store
from google.cloud import storage
from io import BytesIO

# Constants
VERTEXAI = os.getenv("VERTEXAI", "true").lower() == "true"
LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
MODEL_ID = "gemini-2.0-flash-001"
URLS = [
    "https://cloud.google.com/architecture/deploy-operate-generative-ai-applications"
]
BUCKET_NAME = "output-agent-luce"
DESTINATION_BLOB_NAME = "output.txt"
# Initialize Google Cloud clients
credentials, project_id = google.auth.default()
vertexai.init(project=project_id, location=LOCATION)


if VERTEXAI:
    genai_client = genai.Client(project=project_id, location=LOCATION, vertexai=True)
else:
    # API key should be set using GOOGLE_API_KEY environment variable
    genai_client = genai.Client(http_options={"api_version": "v1alpha"})

# Initialize vector store and retriever
embedding = VertexAIEmbeddings(model_name=EMBEDDING_MODEL)
vector_store = get_vector_store(embedding=embedding, urls=URLS)
retriever = vector_store.as_retriever()


def retrieve_docs(query: str) -> dict[str, str]:
    """
    Retrieves pre-formatted documents about MLOps (Machine Learning Operations),
      Gen AI lifecycle, and production deployment best practices.

    Args:
        query: Search query string related to MLOps, Gen AI, or production deployment.

    Returns:
        A set of relevant, pre-formatted documents.
    """
    docs = retriever.invoke(query)
    formatted_docs = FORMAT_DOCS.format(docs=docs)
    return {"output": formatted_docs}

def upload_text_to_gcs(text_content: str):
    """
    Sube un texto a un archivo en Google Cloud Storage.

    :param bucket_name: Nombre del bucket en GCS.
    :param text_content: Contenido del archivo en formato string.
    :param destination_blob_name: Nombre del archivo en GCS.
    """

        # Inicializa el cliente de GCS
    client = storage.Client()

        # Obtiene el bucket
    bucket = client.bucket(BUCKET_NAME)

        # Crea un blob (archivo en GCS)
    blob = bucket.blob(DESTINATION_BLOB_NAME)

        # Sube el contenido como un archivo de texto
    blob.upload_from_string(text_content, content_type="text/plain")


# Configure tools and live connection
retrieve_docs_tool = Tool(
    function_declarations=[
        FunctionDeclaration.from_callable(client=genai_client, callable=retrieve_docs)
    ]
)

upload_text_to_gcs_tool = Tool(
    function_declarations=[
        FunctionDeclaration.from_callable(client=genai_client, callable=upload_text_to_gcs)
    ]
)

tool_functions = {"retrieve_docs": retrieve_docs, "upload_text_to_gcs": upload_text_to_gcs}

live_connect_config = LiveConnectConfig(
    response_modalities=["AUDIO"],
    tools=[retrieve_docs_tool],
    system_instruction=Content(parts=[{"text": SYSTEM_INSTRUCTION}]),
)
