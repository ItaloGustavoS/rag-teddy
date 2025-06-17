import logging
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

logger_llm = logging.getLogger(__name__)

# Carregar modelos e tokenizers uma vez quando o módulo é importado.
# Usar um modelo menor para demonstração.
# Para português, modelos como 'csebuetnlp/mT5_multilingual_XLSum' ou
# 'facebook/mbart-large-50-many-to-many-mmt' fine-tunado para sumarização
# podem ser melhores, mas são maiores.
MODEL_NAME = "google/flan-t5-small"
# Alternativa para sumarização (mais focado em inglês, mas pode funcionar):
# MODEL_NAME_SUMMARIZATION = "sshleifer/distilbart-cnn-6-6"

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    # Para tasks de text2text-generation (como Flan-T5)
    text2text_generator = pipeline(
        "text2text-generation", model=model, tokenizer=tokenizer
    )
    logger_llm.info(f"Modelo LLM '{MODEL_NAME}' carregado com sucesso.")
except Exception as e:
    logger_llm.error(f"Falha ao carregar o modelo LLM '{MODEL_NAME}': {e}")
    text2text_generator = None


def generate_summary(text: str, max_length: int = 150, min_length: int = 30) -> str:
    """
    Gera um sumário do texto usando o modelo LLM carregado.
    """
    if not text2text_generator:
        logger_llm.warning(
            "Gerador LLM não está disponível. Retornando texto original."
        )
        return "Erro: LLM não disponível para sumarização."

    prompt = f"summarize: {text}"

    # Limitar o tamanho do input para evitar erros com o modelo
    # Tokenizers têm um limite máximo de tokens (ex: 512 para T5-small)
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)

    try:
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            min_length=min_length,
            num_beams=4,
            early_stopping=True,
        )
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return summary
    except Exception as e:
        logger_llm.error(f"Erro durante a geração de sumário pelo LLM: {e}")
        return "Erro ao gerar sumário."


def analyze_resume_with_query(
    resume_text: str, query: str, max_length: int = 200
) -> str:
    """
    Analisa o texto do currículo em relação a uma query (requisitos da vaga).
    """
    if not text2text_generator:
        logger_llm.warning(
            "Gerador LLM não está disponível. Retornando análise placeholder."
        )
        return "Erro: LLM não disponível para análise."

    prompt = f'Based on the following resume text, answer the question. Resume text: "{resume_text}". Question: "{query}"'

    inputs = tokenizer(
        prompt, return_tensors="pt", max_length=1024, truncation=True
    )  # Aumentar max_length para query+contexto

    try:
        outputs = model.generate(
            **inputs, max_length=max_length, num_beams=4, early_stopping=True
        )
        analysis = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return analysis
    except Exception as e:
        logger_llm.error(f"Erro durante a análise de currículo pelo LLM: {e}")
        return "Erro ao analisar currículo."
