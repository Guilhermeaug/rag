from typing import List, Dict, Any
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import os
import shutil
from pathlib import Path

from app.core.config.embeddings import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTORSTORE_PATH,
)
from app.core.utils.logger import get_logger
from app.services.document_loaders import load_all_documents, load_document
from app.services.vectorstore_service import VectorstoreService

logger = get_logger(__name__)


class IngestService:
    """
    Serviço para ingestão de documentos no sistema RAG
    """

    @staticmethod
    def ingest_documents(data_dir: str = "data/", clear_existing: bool = False) -> Dict[str, Any]:
        """
        Realiza a ingestão de documentos para o vectorstore

        Args:
            data_dir: Diretório onde estão os documentos
            clear_existing: Se True, limpa o vectorstore existente

        Returns:
            Dicionário com status e mensagem do resultado da operação
        """

        try:
            if not os.path.isdir(data_dir):
                error_msg = f"Diretório de dados não encontrado: {data_dir}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }

            if VectorstoreService.check_vectorstore_exists():
                if not clear_existing:
                    logger.info(f"Vectorstore já existe em: {VECTORSTORE_PATH}. Pulando ingestão.")
                    return {
                        "status": "success",
                        "message": "Vectorstore já existe. Use 'clear_existing=True' para forçar a reingestão."
                    }
                logger.info(f"Removendo vectorstore existente em: {VECTORSTORE_PATH}")
                shutil.rmtree(VECTORSTORE_PATH)
                os.makedirs(VECTORSTORE_PATH, exist_ok=True)

            logger.info(f"Carregando documentos de: {data_dir}")
            documents = load_all_documents(data_dir)

            result = IngestService._process_documents(documents)
            if result["status"] != "success":
                return result

            return IngestService._save_to_vectorstore(result["chunks"], create_new=True)

        except Exception as e:
            error_msg = f"Erro durante a ingestão de documentos: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    @staticmethod
    def _filter_and_prepare_chunks(
            chunks: List[Document]
    ) -> List[Document]:
        """
        Filtra chunks inúteis e prepara os chunks para indexação.

        Args:
            chunks: Lista de chunks a serem filtrados e preparados

        Returns:
            Lista de chunks filtrados e preparados
        """

        filtered_chunks = []

        for chunk in chunks:
            chunk.page_content = f"passage: {chunk.page_content.strip()}"
            filtered_chunks.append(chunk)

        return filtered_chunks

    @staticmethod
    def add_file_to_vectorstore(file_path: str) -> Dict[str, Any]:
        """
        Adiciona um único arquivo à vector store existente

        Args:
            file_path: Caminho para o arquivo a ser adicionado

        Returns:
            Dicionário com status e mensagem do resultado da operação
        """

        try:
            file_path = Path(file_path)

            if not file_path.exists() or not file_path.is_file():
                error_msg = f"Arquivo não encontrado: {file_path}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }

            logger.info(f"Carregando arquivo: {file_path}")
            document = load_document(str(file_path))

            result = IngestService._process_documents(document)
            if result["status"] != "success":
                return result

            return IngestService._save_to_vectorstore(result["chunks"], create_new=False)
        except Exception as e:
            error_msg = f"Erro ao adicionar arquivo à vector store: {e}"
            logger.error(error_msg)

            return {
                "status": "error",
                "message": error_msg
            }

    @staticmethod
    def _process_documents(documents: List[Document]) -> Dict[str, Any]:
        """
        Processa documentos em chunks e retorna chunks filtrados

        Args:
            documents: Lista de documentos a serem processados

        Returns:
            Dicionário com status, mensagem e chunks processados (se houver)
        """

        if not documents:
            return {
                "status": "warning",
                "message": "Nenhum documento foi carregado.",
                "chunks": None
            }

        logger.info("Dividindo em chunks...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(documents)

        logger.info("Filtrando e preparando chunks...")
        filtered_chunks = IngestService._filter_and_prepare_chunks(chunks)

        if not filtered_chunks:
            return {
                "status": "warning",
                "message": "Não foi possível gerar chunks úteis a partir dos documentos.",
                "chunks": None
            }

        return {
            "status": "success",
            "message": "",
            "chunks": filtered_chunks
        }

    @staticmethod
    def _save_to_vectorstore(chunks: List[Document], create_new: bool = False) -> Dict[str, Any]:
        """
        Salva chunks em uma vector store

        Args:
            chunks: Lista de chunks a serem salvos
            create_new: Se True, cria uma nova vector store. Se False, adiciona à existente.

        Returns:
            Dicionário com status e mensagem do resultado da operação
        """

        try:
            if create_new:
                logger.info(f"Gerando embeddings para {len(chunks)} chunks e criando vectorstore...")

                db = FAISS.from_documents(chunks, EMBEDDING_MODEL)
                db.save_local(VECTORSTORE_PATH)

                return {
                    "status": "success",
                    "message": f"Indexação completa! {len(chunks)} chunks foram indexados com sucesso."
                }
            else:
                logger.info(f"Adicionando {len(chunks)} chunks à vector store existente...")

                try:
                    db = VectorstoreService.get_vectorstore()
                    db.add_documents(chunks)
                    db.save_local(VECTORSTORE_PATH)

                    return {
                        "status": "success",
                        "message": f"Adicionados com sucesso! {len(chunks)} chunks foram indexados."
                    }
                except Exception as e:
                    logger.error(f"Erro ao carregar ou atualizar vectorstore: {e}")
                    return {
                        "status": "error",
                        "message": f"Erro ao carregar ou atualizar vectorstore: {e}"
                    }

        except Exception as e:
            logger.error(f"Erro ao salvar na vectorstore: {e}")
            return {
                "status": "error",
                "message": f"Erro ao salvar na vectorstore: {e}"
            }
