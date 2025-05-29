from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.vectorstore_service import VectorstoreService
from app.services.ingest_service import IngestService
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


async def initialize_vectorstore():
    """
    Inicializa o vectorstore, realizando a ingestão se necessário.
    """
    logger.info("Iniciando verificação e carregamento do vectorstore na inicialização da aplicação...")
    if VectorstoreService.check_vectorstore_exists():
        VectorstoreService.load_vectorstore()
        logger.info("Vectorstore carregado com sucesso a partir de local existente.")
    else:
        logger.warning("Vectorstore não encontrado. Iniciando ingestão de documentos...")
        try:
            IngestService.ingest_documents(data_dir="data/", clear_existing=True)
            logger.info("Ingestão de documentos concluída. Carregando vectorstore...")
            VectorstoreService.load_vectorstore()
            logger.info("Vectorstore carregado com sucesso após ingestão.")
        except Exception as e:
            logger.error(f"Falha crítica durante a ingestão de documentos na inicialização: {e}")
            raise e

    logger.info("Inicialização do VectorstoreService concluída.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG para Serviços Públicos",
        description="API para sistema RAG (Retrieval Augmented Generation) para consulta de documentos de serviços públicos",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_event_handler("startup", initialize_vectorstore)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
