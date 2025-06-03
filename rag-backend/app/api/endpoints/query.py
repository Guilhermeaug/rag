# /home/pedro/Documents/Programming/CEFET/TCC - Guilherme/rag/rag-backend/app/api/endpoints/query.py
from fastapi import APIRouter, HTTPException
from app.schemas.rag import QueryRequest, QueryResponse # Seus schemas
from app.services.query_service import QueryService    # Seu serviço
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["Query"]
)

@router.post("", response_model=QueryResponse, status_code=200)
async def query_documents(request: QueryRequest):
    """
    Endpoint para realizar consultas nos documentos indexados.
    """
    logger.info("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    try:
        # A verificação explícita de QueryService.vectorstore não é mais necessária aqui,
        # pois QueryService.process_query (via load_vectorstore) agora lida com isso
        # e levantará HTTPException se o vectorstore não estiver pronto.

        logger.info(f"Recebida consulta no endpoint: '{request.query}' com search_type='{request.search_type}' e k={request.search_k}")
        
        # Chama o método process_query do QueryService
        response_data = await QueryService.process_query(
            query=request.query,
            search_type=request.search_type, # Passa o search_type
            search_k=request.search_k         # Passa o search_k
            # provider, model, temperature, etc., podem continuar com defaults ou serem adicionados aqui
        )
        
        # Mapeia a resposta do QueryService para o QueryResponse do endpoint
        # O QueryResponse espera 'query' e 'results'.
        # QueryService.process_query retorna um dict com 'answer' e 'sources'.
        # Vamos assumir que 'results' no QueryResponse deve ser a 'answer'.
        
        # Você pode querer incluir as fontes na resposta também,
        # se o seu QueryResponse schema for ajustado para isso.
        # Por agora, apenas a resposta:
        final_results = response_data.get("answer", "Não foi possível obter uma resposta do serviço.")
        
        return QueryResponse(
            query=request.query,
            answer=response_data.get("answer", "Não foi possível obter uma resposta."), # Use a chave "answer"
            sources=response_data.get("sources", []) # Use a chave "sources"
        )

    except HTTPException as http_exc:
        # Se QueryService.process_query levantar uma HTTPException (como o 503),
        # ela será capturada aqui e re-levantada.
        logger.error(f"HTTPException durante a consulta: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Captura qualquer outro erro inesperado do QueryService.process_query
        logger.error(f"Erro inesperado no endpoint /query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno inesperado: {str(e)}")