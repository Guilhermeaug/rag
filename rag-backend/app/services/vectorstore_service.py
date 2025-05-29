from langchain_community.vectorstores import FAISS
import os
from typing import Tuple, Any

from app.core.utils.logger import get_logger
from app.core.config.embeddings import EMBEDDING_MODEL, VECTORSTORE_PATH

logger = get_logger(__name__)

class VectorstoreService:
    """
    Serviço centralizado para gerenciamento da vector store
    """
    _db: FAISS = None
    _retriever: Any = None

    @classmethod
    def load_vectorstore(cls) -> Tuple[FAISS, Any]:
        """
        Carrega o vectorstore FAISS e cria um retriever.
        Implementa o padrão singleton para carregar apenas uma vez.

        Returns:
            Uma tupla contendo o vectorstore e o retriever configurado

        Raises:
            Exception: Se ocorrer um erro ao carregar o vectorstore
        """
        if cls._db is not None and cls._retriever is not None:
            return cls._db, cls._retriever

        try:
            logger.info(f"Carregando índice de vetores de: {VECTORSTORE_PATH}")

            if not VectorstoreService.check_vectorstore_exists():
                logger.warning(
                    f"Vectorstore não encontrado ou vazio em {VECTORSTORE_PATH}. É necessário executar a ingestão primeiro ou o diretório está vazio.")
                pass

            db = FAISS.load_local(
                VECTORSTORE_PATH, EMBEDDING_MODEL, allow_dangerous_deserialization=True
            )
            retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})
            logger.info("Índice carregado com sucesso e retriever criado.")

            cls._db = db
            cls._retriever = retriever

            return cls._db, cls._retriever
        except Exception as e:
            logger.error(f"Erro ao carregar índice de vetores: {e}")

            cls._db = None # Garante que não usemos um estado parcialmente carregado
            cls._retriever = None
            raise e

    @classmethod
    def get_retriever(cls) -> Any:
        """
        Retorna o retriever singleton. Carrega se ainda não estiver carregado.
        """
        if cls._retriever is None:
            cls.load_vectorstore()
        return cls._retriever

    @classmethod
    def get_vectorstore(cls) -> FAISS:
        """
        Retorna o vectorstore (db) singleton. Carrega se ainda não estiver carregado.
        """
        if cls._db is None:
            cls.load_vectorstore()
        return cls._db

    @staticmethod
    def check_vectorstore_exists() -> bool:
        """
        Verifica se o vectorstore já existe

        Returns:
            True se o vectorstore existir, False caso contrário
        """
        return os.path.exists(VECTORSTORE_PATH) and len(os.listdir(VECTORSTORE_PATH)) > 0
