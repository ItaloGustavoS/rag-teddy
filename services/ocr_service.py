import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes # Alterado de convert_from_path para processar bytes
import io
import logging

logger_ocr = logging.getLogger(__name__)

# Configure o caminho do Tesseract se não estiver no PATH (comum no Windows)
# No Docker, geralmente está no PATH se instalado corretamente.
# Ex: pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' (Linux)

# Idiomas para Tesseract (Português e Inglês são bons padrões para CVs no Brasil)
TESSERACT_LANG = 'por+eng'

async def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Extrai texto de bytes de uma imagem usando Tesseract OCR.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=TESSERACT_LANG)
        return text.strip()
    except Exception as e:
        logger_ocr.error(f"Erro ao processar imagem com Tesseract: {e}")
        return ""

async def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Converte um PDF (em bytes) para imagens e extrai texto de cada página.
    """
    full_text = ""
    try:
        # O dpi pode ser ajustado para melhor qualidade vs. tempo de processamento
        images = convert_from_bytes(pdf_bytes, dpi=200)
        for i, image in enumerate(images):
            try:
                # Salva a imagem em um buffer de bytes para passar para o Tesseract
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                page_text = await extract_text_from_image_bytes(img_byte_arr)
                full_text += f"\n--- Página {i+1} ---\n{page_text}"
            except Exception as e_page:
                logger_ocr.error(f"Erro ao processar página {i+1} do PDF: {e_page}")
                full_text += f"\n--- Página {i+1} (Erro na extração) ---\n"
        return full_text.strip()
    except Exception as e:
        logger_ocr.error(f"Erro ao converter PDF para imagens: {e}")
        return ""