from http.client import HTTPException
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
    def load_vectorstore(search_type: str = 'similarity', search_k: int = 5) -> Tuple[Any, Any]: # Defina Any para os tipos de vectorstore e retriever
        """
        Carrega (ou obtém) o vectorstore e o retriever do VectorstoreService.
        Este método deve ser chamado ANTES de qualquer tentativa de consulta.
        O vectorstore é esperado estar inicializado pelo IngestService.
        """
        logger.info(f"Carregando vectorstore e retriever via VectorstoreService com search_type='{search_type}', k={search_k}...")
        vectorstore = VectorstoreService.get_vectorstore() # Assumindo que VectorstoreService tem este método

        if not vectorstore:
            logger.error("Vectorstore não está carregado ou inicializado no VectorstoreService. Execute a ingestão de dados primeiro.")
            # Levanta uma exceção que o process_query pode capturar e transformar em HTTPException 503
            raise ValueError("Vectorstore não está carregado. Execute a ingestão de dados primeiro.")

        try:
            # Configurações padrão para o retriever, ajuste conforme necessário
            retriever = vectorstore.as_retriever(
                search_type=search_type, # Usa o search_type recebido
                search_kwargs={"k": search_k, "score_threshold": 0.5} # Usa o search_k recebido
            )
            logger.info("Vectorstore e retriever carregados com sucesso.")
            return vectorstore, retriever
        except Exception as e:
            logger.error(f"Erro ao criar retriever a partir do vectorstore: {e}")
            raise ValueError(f"Não foi possível criar o retriever: {e}")

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
            search_type: str = 'similarity',
            search_k: int = 5,
            provider: LLMProvider = "openai", # Certifique-se que LLMProvider está definido
            model: str = "gpt-4o-mini",
            temperature: float = 0.7,
            max_tokens: int = 4096
    ) -> Dict[str, Any]:
        try:
            logger.info(f"Processando consulta: '{query}' com search_type='{search_type}', k={search_k}, modelo {provider}/{model}")

            vectorstore_instance, retriever = QueryService.load_vectorstore(
                search_type=search_type, 
                search_k=search_k
            )

            # Logar documentos recuperados (MUITO ÚTIL PARA DEBUG)
            if retriever:
                logger.info(f"Recuperando documentos relevantes para a query: '{query}' usando search_type='{search_type}', k={search_k}")
                retrieved_docs = await retriever.aget_relevant_documents(query) # Use aget_ para async
                logger.info(f"Número de documentos recuperados: {len(retrieved_docs)}")
                for i, doc in enumerate(retrieved_docs):
                    logger.debug(f"--- Documento Relevante {i + 1} ---")
                    logger.debug(f"Fonte: {doc.metadata.get('source_doc', 'Desconhecido')}")
                    # Logue um trecho do conteúdo para não poluir demais os logs
                    logger.debug(f"Conteúdo (snippet): {doc.page_content[:250]}...") 
            else:
                logger.warning("Retriever não está disponível. A consulta será feita sem contexto de RAG.")


            llm_kwargs = {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            llm = QueryService.initialize_llm(provider, model, **llm_kwargs)
            qa_chain = QueryService.create_qa_chain(llm, retriever)

            logger.info("Gerando resposta com qa_chain.ainvoke...")
            result = await qa_chain.ainvoke({"input": query})

            # ----> LOG CRÍTICO AQUI <----
            logger.info(f"Resultado COMPLETO da qa_chain.ainvoke: {result}") 

            logger.info("Resposta (supostamente) gerada com sucesso pela qa_chain.")

            sources = []
            if result and result.get("context"): # Adiciona verificação se result existe
                for doc in result.get("context", []):
                    source = doc.metadata.get("source_doc", "Desconhecido")
                    if source not in sources:
                        sources.append(source)

            # Pega o valor de "answer" do resultado da chain.
            # Se "answer" não existir ou for None, o default será usado.
            answer_from_chain = result.get("answer") if result else None # Verifica se result não é None

            if not answer_from_chain:
                logger.warning(f"A chave 'answer' está faltando ou é nula no resultado da qa_chain. Resultado: {result}")
                # Define a resposta padrão se não houver resposta da chain.
                final_answer = "Não foi possível obter uma resposta específica da LLM para esta consulta."
            else:
                final_answer = answer_from_chain

            return {
                "answer": final_answer,
                "sources": sources
            }
        except ValueError as ve:
            logger.error(f"Erro de valor ao processar consulta (ex: vectorstore não carregado): {ve}")
            raise HTTPException(status_code=503, detail=str(ve))
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {e}", exc_info=True) # Adiciona exc_info para traceback completo
            if not isinstance(e, HTTPException):
                raise HTTPException(status_code=500, detail=f"Erro interno ao processar consulta: {str(e)}")
            raise
