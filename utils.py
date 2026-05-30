import re
from urllib.parse import urlparse, unquote
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

# ==================== UTILITÁRIOS DE DETECÇÃO DE URL ====================

class URLDetector:
    """Classe utilitária para detecção e classificação de URLs"""
    
    # Domínios suportados pelo yt-dlp para vídeos
    VIDEO_PLATFORMS = [
        r'youtube\.com', r'youtu\.be', r'vimeo\.com', r'dailymotion\.com',
        r'twitch\.tv', r'facebook\.com/.*/videos', r'instagram\.com/.*/reel',
        r'tiktok\.com', r'x\.com/.*/status', r'twitter\.com/.*/status'
    ]
    
    @classmethod
    def is_youtube_or_video_platform(cls, url: str) -> bool:
        """Verifica se a URL pertence a uma plataforma de vídeo suportada"""
        if not url:
            return False
        url_lower = url.lower()
        for pattern in cls.VIDEO_PLATFORMS:
            if re.search(pattern, url_lower):
                return True
        return False
    
    @classmethod
    def is_valid_http_url(cls, url: str) -> bool:
        """Verifica se a URL é um link HTTP/HTTPS válido"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
        except:
            logging.getLogger("UniversalDownloader").warning(f"⚠️ URL inválida: {url}")
            return False
    
    @classmethod
    def extract_filename_from_url(cls, url: str) -> tuple[str, str]:
        """
        Extrai nome e extensão do arquivo a partir da URL.
        Retorna: (nome_base, extensão_com_ponto)
        """
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)  # Decodifica caracteres URL-encoded
            
            # Tenta obter nome do path
            filename = os.path.basename(path)
            
            # Se não houver nome no path, gera um genérico
            if not filename or filename.endswith('/'):
                filename = f"arquivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            name, ext = os.path.splitext(filename)
            # Limpa caracteres inválidos para nome de arquivo
            name = re.sub(r'[<>:"/\\|?*]', '_', name)
            ext = ext.lower() if ext else '.bin'
            
            return name, ext
        except Exception as e:
            logging.getLogger("UniversalDownloader").warning(f"⚠️ Falha ao extrair nome da URL: {e}")
            return f"arquivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}", '.bin'
    
    @classmethod
    def classify_url(cls, url: str) -> str:
        """
        Classifica o tipo de URL para roteamento.
        Retorna: 'video' | 'generic' | 'invalid'
        """
        if not cls.is_valid_http_url(url):
            return 'invalid'
        if cls.is_youtube_or_video_platform(url):
            return 'video'
        return 'generic'