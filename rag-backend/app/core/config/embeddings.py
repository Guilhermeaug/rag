from langchain_huggingface import HuggingFaceEmbeddings
from torch import cuda
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

device = "cuda" if cuda.is_available() else "cpu"
# logger.info(f"Using device: {device} for embeddings")

EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-base",
    model_kwargs={"device": device},
    encode_kwargs={"normalize_embeddings": True},
)
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
VECTORSTORE_PATH = "embeddings/index"
