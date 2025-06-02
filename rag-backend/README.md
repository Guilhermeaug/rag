# RAG para Serviços Públicos

Este projeto implementa um sistema RAG (Retrieval Augmented Generation) para consulta de documentos de serviços públicos. Ele permite a ingestão de documentos em vários formatos e consultas em linguagem natural, usando modelos de linguagem para gerar respostas baseadas nos documentos indexados.

## Estrutura do Projeto

```
rag-backend/
├── main.py               # Aplicação FastAPI principal
├── pyproject.toml        # Configuração do projeto e dependências
├── uv.lock               # Arquivo de lock do UV
├── data/                 # Diretório para armazenar documentos
├── embeddings/           # Diretório para armazenar os embeddings/índices
└── src/
    ├── config.py         # Configurações gerais
    ├── ingestion/        # Módulo de ingestão de documentos
    │   ├── document_loaders.py
    │   └── ingest.py
    ├── retrieval/        # Módulo de recuperação e consulta
    │   ├── config.py
    │   ├── llm_config.py
    │   └── retrieve.py
    └── utils/            # Utilitários
        └── logger.py
```

## Requisitos

- Python 3.9+
- UV (gerenciador de pacotes Python)
- Para OCR em PDFs, é necessário o Tesseract OCR instalado

## Configuração

1. Clone o repositório:
```
git clone <repository-url>
cd rag-public-services/rag-backend
```

2. Instale as dependências com UV:
```
uv pip install -e .

uv sync
```

3. Configure as variáveis de ambiente (crie um arquivo `.env` na raiz do projeto):
```
OPENAI_API_KEY=sua_chave_da_openai
GOOGLE_API_KEY=sua_chave_do_google
```

## Uso

### Iniciar o servidor

```
python main.py

uv run main.py
```

Isso iniciará o servidor FastAPI na porta 8000.

### Acesso à documentação da API

Após iniciar o servidor, acesse:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Endpoints principais

#### 1. Ingestão de documentos

```
POST /ingest
```

Exemplo de corpo da requisição:
```json
{
  "data_dir": "data/",
  "clear_existing": false
}
```

#### 2. Consulta de documentos

```
POST /query
```

Exemplo de corpo da requisição:
```json
{
  "query": "O que é necessário para fazer um pedido de patente?",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

## Formatos de documentos suportados

- PDF (com e sem OCR)
- DOCX/DOC
- XLS/XLSX
- TXT
- MD

## Integração com diferentes LLMs

O sistema suporta integração com diferentes provedores de LLM:
- OpenAI
- Google AI (Gemini)
- Ollama (para modelos locais)

## Troubleshooting

### Problemas comuns:

1. **Erro ao carregar o vectorstore:**
   - Certifique-se de que a ingestão foi executada pelo menos uma vez.

2. **Erro na ingestão de PDFs:**
   - Para PDFs que requerem OCR, verifique se o Tesseract está instalado.

3. **Respostas imprecisas:**
   - Tente ajustar os parâmetros como temperatura e número de documentos recuperados.
