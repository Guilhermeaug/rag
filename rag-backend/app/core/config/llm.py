from langchain_openai import OpenAI
from langchain_google_genai import GoogleGenerativeAI
from langchain_ollama import OllamaLLM
from typing import Literal, Optional, Union
import logging
logger = logging.getLogger(__name__)

LLMProvider = Literal["openai", "google", "ollama"]

DEFAULT_PROVIDER: LLMProvider = "openai"

LLM_CONFIGS = {
    "openai": {
        "class": OpenAI,
        "default_model": "gpt-4o-mini",
        "required_params": ["model"],
        "optional_params": ["temperature", "max_tokens"],
    },
    "google": {
        "class": GoogleGenerativeAI,
        "default_model": "gemini-2.0-flash",
        "required_params": ["model"],
        "optional_params": ["temperature", "max_tokens"],
    },
    "ollama": {
        "class": OllamaLLM,
        "default_model": "deepseek-r1:8b",
        "required_params": ["model"],
        "optional_params": ["temperature", "max_tokens"],
    },
}


def get_llm(
    provider: LLMProvider = DEFAULT_PROVIDER, model: Optional[str] = None, **kwargs
) -> Union[OpenAI, GoogleGenerativeAI, OllamaLLM]:
    """
    Inicializa e retorna um modelo de linguagem baseado no provedor especificado.
    # ... (resto da sua docstring)
    """
    if provider not in LLM_CONFIGS:
        logger.error(f"Provedor de LLM não suportado: {provider}")
        raise ValueError(f"Provedor de LLM não suportado: {provider}")

    config = LLM_CONFIGS[provider]
    llm_class = config["class"]
    
    # Determina o nome/ID do modelo a ser usado
    model_id_to_use = model or config["default_model"]
    
    # Determina a chave correta para o parâmetro do modelo (ex: "model_name" ou "model")
    model_param_key = config.get("model_param_key", "model") # Usa "model" como padrão se não especificado

    # Cria um dicionário para os parâmetros finais que serão passados para a classe LLM.
    # Começa com uma cópia dos kwargs recebidos (que contêm temperature, max_tokens de QueryService).
    final_llm_params = kwargs.copy()

    # Define o parâmetro do modelo com a chave correta e o valor determinado.
    final_llm_params[model_param_key] = model_id_to_use
    
    # Se 'model' ou 'model_name' estiverem nos kwargs originais e forem diferentes
    # da model_param_key que estamos usando, removemos para evitar conflitos.
    # (Ex: se model_param_key é 'model_name', removemos 'model' dos kwargs se existir)
    if model_param_key != "model" and "model" in final_llm_params:
        del final_llm_params["model"]
    if model_param_key != "model_name" and "model_name" in final_llm_params:
        del final_llm_params["model_name"]

    # Os valores de 'max_tokens' e 'temperature' já estão em final_llm_params
    # se foram passados por QueryService via kwargs.
    # Se você quiser definir padrões NESSA FUNÇÃO caso QueryService não os envie:
    if "max_tokens" not in final_llm_params:
        final_llm_params["max_tokens"] = config.get("default_max_tokens", 4096) # Pega de config ou um valor geral
    if "temperature" not in final_llm_params:
        final_llm_params["temperature"] = config.get("default_temperature", 0.7) # Pega de config ou um valor geral
    
    # Adicione aqui quaisquer outros parâmetros obrigatórios ou padrão específicos do provedor
    # que não são cobertos pelos kwargs genéricos, se necessário.
    # Por exemplo, API keys podem ser tratadas aqui se não forem gerenciadas automaticamente pela Langchain
    # api_key_env_var = config.get("api_key_env")
    # if api_key_env_var and os.getenv(api_key_env_var):
    #     # O nome do parâmetro da API key varia (ex: 'api_key', 'openai_api_key', 'google_api_key')
    #     # Adicione a chave correta a final_llm_params
    #     if provider == LLMProvider.OPENAI:
    #         final_llm_params["openai_api_key"] = os.getenv(api_key_env_var)
    #     elif provider == LLMProvider.GOOGLE:
    #          final_llm_params["google_api_key"] = os.getenv(api_key_env_var)
    # Ou, se a classe LLM lida com as variáveis de ambiente automaticamente, isso não é necessário.


    logger.debug(f"Instanciando {llm_class.__name__} com os parâmetros: {final_llm_params}")
    try:
        return llm_class(**final_llm_params)
    except TypeError as e:
        logger.error(f"TypeError ao instanciar LLM {llm_class.__name__} com parâmetros {final_llm_params}: {e}")
        # Este log é útil para depurar quais parâmetros exatos causaram o TypeError
        raise
    except Exception as e:
        logger.error(f"Erro genérico ao instanciar LLM {llm_class.__name__}: {e}")
        raise

