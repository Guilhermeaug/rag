from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
from typing import Dict, Any, Tuple

from app.core.utils.logger import get_logger
from app.core.config.embeddings import EMBEDDING_MODEL
from app.core.config.prompts import TEMPLATE
from app.core.config.llm import get_llm, LLMProvider
from app.services.vectorstore_service import VectorstoreService

load_dotenv()

logger = get_logger(__name__)


class QueryService:
    @staticmethod
    def initialize_llm(provider: LLMProvider = "openai", model: str = "gpt-4o-mini", **kwargs) -> Any:
        """
        Inicializa um modelo de linguagem (LLM).

        Args:
            provider: Provedor do LLM ("openai", "google", "ollama")
            model: Nome do modelo a ser usado
            **kwargs: Parâmetros adicionais para o LLM

        Returns:
            Instância do LLM configurado

        Raises:
            Exception: Se ocorrer um erro ao inicializar o LLM
        """
        try:
            logger.info(f"Inicializando modelo de linguagem (LLM) - Provider: {provider}, Model: {model}")
            llm = get_llm(provider=provider, model=model, **kwargs)
            logger.info(f"Modelo de linguagem inicializado com sucesso")
            return llm
        except Exception as e:
            logger.error(f"Erro ao inicializar o modelo de linguagem: {e}")
            raise

    @staticmethod
    def create_qa_chain(llm, retriever) -> Any:
        """
        Cria uma cadeia de processamento RAG para perguntas e respostas.

        Args:
            llm: Modelo de linguagem inicializado
            retriever: Retriever configurado para busca de documentos

        Returns:
            Cadeia de processamento RAG para perguntas e respostas

        Raises:
            Exception: Se ocorrer um erro ao configurar a cadeia
        """
        try:
            logger.info("Configurando cadeia de processamento RAG")

            document_chain_prompt = PromptTemplate(
                input_variables=["context", "input"],
                template=TEMPLATE,
            )
            combine_docs_chain = create_stuff_documents_chain(llm, document_chain_prompt)
            qa_chain = create_retrieval_chain(retriever, combine_docs_chain)

            logger.info("Cadeia de processamento RAG configurada com sucesso")
            return qa_chain
        except Exception as e:
            logger.error(f"Erro ao configurar cadeia de processamento RAG: {e}")
            raise

    @staticmethod
    async def process_query(
            query: str,
            provider: LLMProvider = "openai",
            model: str = "gpt-4o-mini",
            temperature: float = 0.7,
            max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Processa uma consulta usando o sistema RAG.

        Args:
            query: Pergunta do usuário
            provider: Provedor do LLM
            model: Nome do modelo a ser usado
            temperature: Temperatura para geração de texto
            max_tokens: Número máximo de tokens na resposta

        Returns:
            Dicionário com a resposta e fontes utilizadas

        Raises:
            Exception: Se ocorrer um erro durante o processamento da consulta
        """
        try:
            logger.info(f"Processando consulta: '{query}' com modelo {provider}/{model}")

            # Carregar vectorstore e retriever
            _, retriever = QueryService.load_vectorstore()

            # Inicializar LLM
            llm_kwargs = {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            llm = QueryService.initialize_llm(provider, model, **llm_kwargs)

            # Criar cadeia de QA
            qa_chain = QueryService.create_qa_chain(llm, retriever)

            # Formatar a query
            formatted_query = f"query: {query}"

            # Recuperar documentos para depuração
            retrieved_docs = retriever.get_relevant_documents(formatted_query)
            for i, doc in enumerate(retrieved_docs):
                logger.debug(f"--- Documento {i + 1} ---")
                logger.debug(f"Fonte: {doc.metadata.get('source_doc', 'Desconhecido')}")
                logger.debug(f"Conteúdo: {doc.page_content}")

            # Gerar resposta
            logger.info("Gerando resposta...")
            result = qa_chain.invoke({"input": formatted_query})
            logger.info("Resposta gerada com sucesso")

            # Extrair fontes
            sources = []
            for doc in result.get("context", []):
                source = doc.metadata.get("source_doc", "Desconhecido")
                if source not in sources:
                    sources.append(source)

            return {
                "answer": result.get("answer", "Não foi possível gerar uma resposta."),
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {e}")
            raise
