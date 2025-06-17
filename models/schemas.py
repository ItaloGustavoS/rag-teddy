from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Union, Any
import uuid
from datetime import datetime

class ResumeBase(BaseModel):
    file_name: str

class ResumeSummary(ResumeBase):
    summary: str

class ResumeAnalysis(ResumeBase):
    analysis: str # Pode ser uma justificativa, score, etc.

class ProcessRequest(BaseModel):
    user_id: str = Field(..., example="fabio_techmatch")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), example="a1b2c3d4-e5f6-7890-1234-56789abcdef0")
    query: Optional[str] = Field(None, example="Engenheiro de Software com Python, Django e Docker.")

class SummaryResponse(BaseModel):
    request_id: str
    results: List[ResumeSummary]

class AnalysisResponse(BaseModel):
    request_id: str
    query_used: str
    results: List[ResumeAnalysis]

class LogEntry(BaseModel):
    request_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_text: Optional[str] = None
    # Armazenar um resumo do resultado para evitar sobrecarga no log.
    # Pode ser o número de arquivos processados, ou um breve status.
    result_summary: Any # Dict ou string representando o resultado