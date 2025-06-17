from pymongo import MongoClient
from datetime import datetime
import os
import logging
# from app.models.schemas import LogEntry # Evitar import circular se db_service for usado em schemas

logger_db = logging.getLogger(__name__)

# Carregar configurações do MongoDB do ambiente
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "resume_analyzer_logs")

try:
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    logs_collection = db["usage_logs"]
    # Testar a conexão
    client.admin.command('ping')
    logger_db.info(f"Conectado ao MongoDB em {MONGODB_URI}, database '{DATABASE_NAME}'.")
except Exception as e:
    logger_db.error(f"Falha ao conectar ao MongoDB: {e}")
    client = None
    db = None
    logs_collection = None

async def log_usage(request_id: str, user_id: str, query_text: Optional[str], result_summary: Any):
    """
    Registra uma entrada de log no MongoDB.
    """
    if not logs_collection:
        logger_db.error("Coleção de logs não disponível. Log não será salvo.")
        return

    log_document = {
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
        "query_text": query_text,
        "result_summary": result_summary # Pode ser um dict com contagens, ou string
    }
    try:
        logs_collection.insert_one(log_document)
        logger_db.info(f"Log salvo para request_id: {request_id}")
    except Exception as e:
        logger_db.error(f"Erro ao salvar log no MongoDB: {e}")