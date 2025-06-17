import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from typing import List, Optional, Union

# Para execução direta ou via uvicorn sem ser um pacote instalado:
from app.services.ocr_service import (
    extract_text_from_image_bytes,
    extract_text_from_pdf_bytes,
)
from app.services.llm_service import generate_summary, analyze_resume_with_query
from app.services.db_service import (
    log_usage,
)  # , logs_collection # logs_collection não é usado diretamente aqui
from app.models.schemas import (
    SummaryResponse,
    AnalysisResponse,
    ResumeSummary,
    ResumeAnalysis,
)

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger_main = logging.getLogger(__name__)

app = FastAPI(
    title="Analisador Inteligente de Currículos - TechMatch",
    description="Processa currículos (PDF/Imagem), extrai texto, sumariza ou analisa com base em uma query.",
    version="0.1.0",
)

# Tipos de arquivo permitidos
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


def get_file_extension(filename: str) -> Optional[str]:
    return filename.split(".")[-1].lower() if "." in filename else None


@app.post(
    "/process_resumes",
    response_model=Union[SummaryResponse, AnalysisResponse],
    summary="Processa currículos para sumarização ou análise baseada em query",
    tags=["Currículos"],
)
async def process_resumes_endpoint(
    files: List[UploadFile] = File(
        ..., description="Lista de arquivos de currículo (PDF, JPG, PNG)"
    ),
    user_id: str = Form(
        ..., description="Identificador do solicitante", example="fabio_techmatch"
    ),
    request_id: str = Form(
        ...,
        description="ID único da requisição (UUID v4)",
        example="a1b2c3d4-e89b-12d3-a456-426614174000",
    ),
    query: Optional[str] = Form(
        None,
        description="Query com requisitos da vaga. Se omitido, retorna sumários.",
        example="Engenheiro de Software com Python e AWS",
    ),
):
    """
    Endpoint para processar múltiplos currículos.
    - Se `query` for fornecida, analisa os currículos em relação à query.
    - Se `query` for omitida, gera um sumário para cada currículo.
    """
    logger_main.info(
        f"Requisição {request_id} recebida de {user_id}. Query: '{query if query else 'N/A'}'"
    )

    processed_results = []
    log_result_summary = {
        "files_processed": 0,
        "files_failed": 0,
        "operation_type": "summary" if not query else "analysis",
    }

    # Validação dos arquivos
    for file in files:
        if file.content_type not in ALLOWED_MIME_TYPES:
            logger_main.warning(
                f"Arquivo {file.filename} com tipo MIME inválido: {file.content_type}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo inválido: {file.filename}. Tipos permitidos: {', '.join(ALLOWED_MIME_TYPES)}",
            )
         ext = get_file_extension(file.filename)
         if not ext or ext not in ALLOWED_EXTENSIONS:
             raise HTTPException(status_code=400, detail=f"Extensão de arquivo inválida: {file.filename}")

    for file in files:
        try:
            logger_main.info(
                f"Processando arquivo: {file.filename} para request {request_id}"
            )
            file_bytes = await file.read()
            text_content = ""

            if file.content_type == "application/pdf":
                text_content = await extract_text_from_pdf_bytes(file_bytes)
            elif file.content_type in ("image/png", "image/jpeg"):
                text_content = await extract_text_from_image_bytes(file_bytes)
            else:
                # Isso já deve ser pego pela validação de MIME type acima, mas é uma segurança extra
                logger_main.warning(
                    f"Tipo de arquivo não suportado para {file.filename} na request {request_id}"
                )
                processed_results.append(
                    {
                        "file_name": file.filename,
                        "error": "Tipo de arquivo não suportado ou erro na leitura inicial.",
                    }
                )
                log_result_summary["files_failed"] += 1
                continue

            await file.close()  # Fechar o arquivo após a leitura

            if not text_content.strip():
                logger_main.warning(
                    f"Nenhum texto extraído de {file.filename} para request {request_id}"
                )
                if query:
                    processed_results.append(
                        ResumeAnalysis(
                            file_name=file.filename,
                            analysis="Nenhum texto extraído do arquivo.",
                        )
                    )
                else:
                    processed_results.append(
                        ResumeSummary(
                            file_name=file.filename,
                            summary="Nenhum texto extraído do arquivo.",
                        )
                    )
                log_result_summary["files_failed"] += 1
                continue

            if query:
                # Análise baseada na query
                analysis_result = analyze_resume_with_query(text_content, query)
                processed_results.append(
                    ResumeAnalysis(file_name=file.filename, analysis=analysis_result)
                )
            else:
                # Sumarização
                summary_result = generate_summary(text_content)
                processed_results.append(
                    ResumeSummary(file_name=file.filename, summary=summary_result)
                )

            log_result_summary["files_processed"] += 1

        except Exception as e:
            logger_main.error(
                f"Erro ao processar o arquivo {file.filename} para request {request_id}: {e}",
                exc_info=True,
            )
            # Adiciona um resultado de erro para este arquivo específico
            error_message = f"Erro ao processar o arquivo: {str(e)}"
            if query:
                processed_results.append(
                    ResumeAnalysis(file_name=file.filename, analysis=error_message)
                )
            else:
                processed_results.append(
                    ResumeSummary(file_name=file.filename, summary=error_message)
                )
            log_result_summary["files_failed"] += 1
            # Considerar se deve parar todo o processamento ou continuar com outros arquivos
            # Por ora, continua com outros arquivos.

    # Registrar o uso
    await log_usage(request_id, user_id, query, log_result_summary)

    if query:
        return AnalysisResponse(
            request_id=request_id, query_used=query, results=processed_results
        )
    else:
        return SummaryResponse(request_id=request_id, results=processed_results)


@app.get("/health", summary="Verifica a saúde da aplicação", tags=["Saúde"])
async def health_check():
    """
    Endpoint simples para verificar se a aplicação está rodando.
    """
    # Poderia adicionar verificações de conexão com DB, LLM, etc.
    return {
        "status": "ok",
        "message": "Serviço de análise de currículos está operacional.",
    }


#Ponto de entrada para Uvicorn se executado diretamente (python app/main.py)
if __name__ == "__main__":
   import uvicorn
# Note: o reload=True é para desenvolvimento.   O Docker CMD não usará --reload a menos que especificado no docker-compose.yml
uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
