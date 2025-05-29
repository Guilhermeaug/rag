from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
import os
import tempfile
from app.schemas.rag import FileUploadResponse
from app.services.ingest_service import IngestService
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/ingest",
    tags=["Ingestion"]
)

@router.post("/upload", response_model=FileUploadResponse, status_code=202)
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Endpoint para adicionar um único arquivo à vectorstore de forma assíncrona.

    Este endpoint recebe um arquivo via upload, salva-o temporariamente,
    e inicia o processamento assíncrono para adicioná-lo à vectorstore existente.
    Os formatos suportados incluem PDF, DOCX, DOC, TXT, MD e XLS/XLSX.
    """
    try:
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)

        with open(temp_file_path, "wb") as f:
            f.write(await file.read())

        logger.info(f"Arquivo temporário salvo em: {temp_file_path}")

        background_tasks.add_task(
            process_file_in_background,
            temp_file_path,
            temp_dir
        )

        return {
            "status": "accepted",
            "message": f"Arquivo '{file.filename}' recebido e está sendo processado em background."
        }
    except Exception as e:
        error_msg = f"Erro durante o upload do arquivo: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


async def process_file_in_background(file_path: str, temp_dir: str):
    """
    Processa um arquivo em background, adicionando-o à vectorstore.

    Args:
        file_path: Caminho para o arquivo temporário
        temp_dir: Diretório temporário que deve ser limpo após o processamento
    """
    try:
        logger.info(f"Iniciando processamento em background do arquivo: {file_path}")
        result = IngestService.add_file_to_vectorstore(file_path)

        if result["status"] == "success":
            logger.info(f"Processamento em background concluído com sucesso: {result['message']}")
        else:
            logger.error(f"Falha no processamento em background: {result['message']}")
    except Exception as e:
        logger.error(f"Erro durante o processamento em background: {e}")
    finally:
        try:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário removido: {temp_dir}")
        except Exception as e:
            logger.error(f"Erro ao limpar diretório temporário: {e}")
