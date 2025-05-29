from fastapi import APIRouter, HTTPException
from app.schemas.rag import QueryRequest, QueryResponse
from app.services.query_service import QueryService
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
    try:
        # Simulação de uma resposta de consulta
        # Substitua pela lógica real de consulta ao seu QueryService
        if not QueryService.vectorstore:
            raise HTTPException(status_code=503, detail="Vectorstore não está carregado. Execute a ingestão primeiro.")

        results = QueryService.query(request.query)
        return QueryResponse(query=request.query, results=results)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Erro durante a consulta: {e}")
        raise HTTPException(status_code=500, detail=f"Erro durante a consulta: {str(e)}")

