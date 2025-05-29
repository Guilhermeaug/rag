import uvicorn
from app.core.app_factory import create_app
from app.api.api import router

app = create_app()

app.include_router(router)

# Para iniciar a aplicação diretamente com python main.py
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
