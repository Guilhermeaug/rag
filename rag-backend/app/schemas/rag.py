from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class QueryRequest(BaseModel):
    query: str = Field(..., description="Pergunta do usuário em linguagem natural")
    provider: Optional[str] = Field(default="openai", description="Provedor do modelo de linguagem")
    model: Optional[str] = Field(default="gpt-4o-mini", description="Nome do modelo de linguagem")
    temperature: Optional[float] = Field(default=0.7, description="Temperatura para geração de texto (0.0 a 1.0)")
    max_tokens: Optional[int] = Field(default=4096, description="Número máximo de tokens na resposta")

    search_type: Optional[Literal['similarity', 'mmr']] = Field(default='similarity', description="Tipo de busca para o retriever")
    search_k: Optional[int] = Field(default=5, ge=1, le=20, description="Número de documentos a serem recuperados (k)")

class IngestRequest(BaseModel):
    data_dir: Optional[str] = Field(default="data/", description="Diretório onde estão os documentos")
    clear_existing: Optional[bool] = Field(default=False, description="Se verdadeiro, limpa o índice existente")

class FileUploadResponse(BaseModel):
    status: str = Field(..., description="Status da operação de upload")
    message: str = Field(..., description="Mensagem detalhada sobre o resultado do upload")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="Resposta gerada pelo modelo")
    sources: List[str] = Field(..., description="Fontes utilizadas para gerar a resposta")

class IngestResponse(BaseModel):
    status: str = Field(..., description="Status da operação de ingestão")
    message: str = Field(..., description="Mensagem detalhada sobre o resultado da ingestão")
