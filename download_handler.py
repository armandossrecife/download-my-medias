import logging
import os
from pathlib import Path
import requests
import yt_dlp
from utils import URLDetector

# ==================== BACKEND: YT-DLP (VÍDEOS) ====================

class VideoDownloader:
    """Gerenciador de downloads de vídeos usando yt-dlp"""
    
    def __init__(self, output_dir="videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.logger = logging.getLogger("UniversalDownloader.Video")

    def download(self, url: str, progress_cb, complete_cb, error_cb):
        self.logger.info(f"🎬 [VIDEO] Iniciando download: {url}")
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.output_dir, '%(title)s [%(id)s].%(ext)s'),
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'progress_hooks': [lambda d: self._progress_hook(d, progress_cb)],
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'retries': 15,
                'fragment_retries': 15,
                'socket_timeout': 30,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.debug("🔍 Extraindo metadados do vídeo...")
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise yt_dlp.utils.DownloadError("Metadados não retornados pelo servidor")

                title = info.get('title', 'Video_Desconhecido')
                vid_id = info.get('id', 'N/A')
                self.logger.info(f"📹 Vídeo identificado: '{title}' (ID: {vid_id})")
                self.logger.debug(f"📦 Duração: {info.get('duration')}s | Views: {info.get('view_count')}")

                self.logger.info("⬇️ Iniciando transferência de dados...")
                ydl.download([url])

                final_path = ydl.prepare_filename(info)
                self.logger.info(f"✅ Download concluído: {Path(final_path).name}")
                complete_cb(title, final_path, 'video')

        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e)
            self.logger.error(f"❌ Erro de download de vídeo: {err_msg}")
            if "HTTP Error 400" in err_msg:
                self.logger.warning("⚠️ HTTP 400: vídeo pode estar restrito ou bloqueado.")
            error_cb(err_msg)
        except Exception as e:
            self.logger.exception(f"💥 Falha crítica no download de vídeo: {type(e).__name__}")
            error_cb(f"{type(e).__name__}: {str(e)}")
        finally:
            self.logger.debug("🏁 Thread de download de vídeo finalizada.")

    def _progress_hook(self, d, callback):
        """Converte progresso do yt-dlp para callback da UI"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                pct = min(100, int((downloaded / total) * 100))
                if pct % 10 == 0 or pct == 1:
                    self.logger.debug(f"📊 [VIDEO] Progresso: {pct}% ({downloaded:,}/{total:,} bytes)")
                callback(pct)

# ==================== BACKEND: REQUESTS (ARQUIVOS GENÉRICOS) ====================

class GenericDownloader:
    """Gerenciador de downloads de arquivos genéricos usando requests"""
    
    def __init__(self, output_dir="arquivos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.logger = logging.getLogger("UniversalDownloader.Generic")

    def download(self, url: str, progress_cb, complete_cb, error_cb):
        self.logger.info(f"📄 [GENERIC] Iniciando download: {url}")
        try:
            # Extrai nome do arquivo da URL
            name, ext = URLDetector.extract_filename_from_url(url)
            filename = f"{name}{ext}"
            filepath = os.path.join(self.output_dir, filename)
            
            # Resolve conflitos de nome
            counter = 1
            while os.path.exists(filepath):
                filename = f"{name}_{counter}{ext}"
                filepath = os.path.join(self.output_dir, filename)
                counter += 1
            
            self.logger.debug(f"📁 Arquivo destino: {filepath}")
            
            # Inicia download com streaming
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            self.logger.info(f"⬇️ Transferindo: {filename} ({total_size:,} bytes)")
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = min(100, int((downloaded / total_size) * 100))
                            if pct % 10 == 0 or pct == 1:
                                self.logger.debug(f"📊 [GENERIC] Progresso: {pct}% ({downloaded:,}/{total_size:,} bytes)")
                            progress_cb(pct)
            
            self.logger.info(f"✅ Download concluído: {filename}")
            complete_cb(filename, filepath, 'generic')
            
        except requests.exceptions.MissingSchema:
            err_msg = "URL inválida. Use http:// ou https://"
            self.logger.error(f"❌ Erro de esquema: {err_msg}")
            error_cb(err_msg)
        except requests.exceptions.ConnectionError:
            err_msg = "Erro de conexão. Verifique sua internet."
            self.logger.error(f"❌ Erro de conexão: {err_msg}")
            error_cb(err_msg)
        except requests.exceptions.Timeout:
            err_msg = "Timeout na conexão. Servidor não respondeu."
            self.logger.error(f"❌ Timeout: {err_msg}")
            error_cb(err_msg)
        except requests.exceptions.HTTPError as e:
            err_msg = f"Erro HTTP {e.response.status_code}: {e.response.reason}"
            self.logger.error(f"❌ {err_msg}")
            error_cb(err_msg)
        except Exception as e:
            self.logger.exception(f"💥 Falha crítica no download genérico: {type(e).__name__}")
            error_cb(f"{type(e).__name__}: {str(e)}")
        finally:
            self.logger.debug("🏁 Thread de download genérico finalizada.")

# ==================== FACADE: ROUTER DE DOWNLOADS ====================

class DownloadRouter:
    """Facade que roteia URLs para o backend apropriado"""
    
    def __init__(self, video_dir="videos", generic_dir="arquivos"):
        self.video_downloader = VideoDownloader(output_dir=video_dir)
        self.generic_downloader = GenericDownloader(output_dir=generic_dir)
        self.logger = logging.getLogger("UniversalDownloader.Router")
    
    def download(self, url: str, progress_cb, complete_cb, error_cb):
        """
        Roteia a URL para o backend correto baseado na classificação.
        
        Args:
            url: URL a ser baixada
            progress_cb: Callback(int) para atualização de progresso
            complete_cb: Callback(str, str, str) para conclusão: (nome, path, tipo)
            error_cb: Callback(str) para tratamento de erros
        """
        url_type = URLDetector.classify_url(url)
        self.logger.info(f"🔍 Classificação da URL '{url[:50]}...': {url_type}")
        
        if url_type == 'invalid':
            error_msg = "URL inválida. Use um link http:// ou https:// válido."
            self.logger.error(f"❌ {error_msg}")
            error_cb(error_msg)
            return
        
        if url_type == 'video':
            self.logger.info("🎬 Roteando para backend de vídeo (yt-dlp)")
            self.video_downloader.download(url, progress_cb, complete_cb, error_cb)
        else:  # generic
            self.logger.info("📄 Roteando para backend genérico (requests)")
            self.generic_downloader.download(url, progress_cb, complete_cb, error_cb)
    
    def set_output_dirs(self, video_dir: str, generic_dir: str):
        """Atualiza os diretórios de saída para ambos os backends"""
        self.video_downloader.output_dir = video_dir
        self.generic_downloader.output_dir = generic_dir
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(generic_dir, exist_ok=True)
        self.logger.info(f"📁 Diretórios atualizados: videos={video_dir}, arquivos={generic_dir}")

