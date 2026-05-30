"""
Universal Downloader - YouTube + Arquivos Genéricos
Versão: 4.0
Autor: Armando Soares Sousa
Data: 2026

Descrição:
    Aplicação que detecta automaticamente o tipo de URL e realiza download:
    - YouTube/Video platforms → yt-dlp → pasta videos/
    - URLs genéricas (http/https) → requests → pasta arquivos/

Requisitos:
    pip install yt-dlp requests
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import requests
import os
import threading
import logging
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

# ==================== CONFIGURAÇÃO DE LOGGING ====================

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"downloader_{timestamp}.log")

class TkinterLogHandler(logging.Handler):
    """Handler customizado para exibir logs em um widget Text do Tkinter"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.max_lines = 2000

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
        
        if int(self.text_widget.index('end-1c').split('.')[0]) > self.max_lines:
            self.text_widget.delete(1.0, f"{self.max_lines}.0")

def setup_logging(text_widget=None):
    """Configura o sistema de logs: Arquivo + Console + UI (opcional)"""
    logger = logging.getLogger("UniversalDownloader")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Arquivo de log
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 2. Console (Terminal)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # 3. Interface Tkinter (se fornecido)
    if text_widget:
        th = TkinterLogHandler(text_widget)
        th.setLevel(logging.INFO)
        th.setFormatter(fmt)
        logger.addHandler(th)

    return logger

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

# ==================== INTERFACE GRÁFICA ====================

class MainWindow:
    def __init__(self, root, title="Universal Downloader v4.0"):
        self.root = root
        self.root.title(title)
        self.root.geometry("750x800")
        self.root.minsize(650, 700)

        self.logger = logging.getLogger("UniversalDownloader.UI")
        self.router = DownloadRouter()
        self.is_downloading = False
        self.current_url_type = None

        self._setup_ui()

    def _setup_ui(self):
        """Cria e organiza todos os widgets da interface"""
        
        # === Frame de Entrada ===
        self.input_frame = ttk.Frame(self.root, padding=10)
        self.input_frame.pack(fill=tk.X)

        self.url_var = tk.StringVar()
        ttk.Label(self.input_frame, text="🔗 URL do arquivo ou vídeo:").grid(row=0, column=0, sticky=tk.W, pady=(0,5))
        
        self.url_entry = ttk.Entry(self.input_frame, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(0,10))
        self.url_entry.bind('<Return>', lambda e: self.start_download())
        
        # Botão de detecção automática
        self.detect_btn = ttk.Button(self.input_frame, text="🔍 Detectar", command=self._detect_url_type)
        self.detect_btn.grid(row=1, column=3, padx=(5,0), sticky=tk.E)
        
        # Label de tipo detectado
        self.type_label = ttk.Label(self.input_frame, text="", font=('', 9, 'italic'))
        self.type_label.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(0,5))

        # Botões de ação
        btn_frame = ttk.Frame(self.input_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, sticky=tk.EW)
        
        self.download_btn = ttk.Button(btn_frame, text="⬇️ Baixar", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=(0,5))
        
        ttk.Button(btn_frame, text="📁 Configurar Pastas", command=self._configure_folders).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(btn_frame, text="📂 Abrir Videos", command=lambda: self._open_folder(self.router.video_downloader.output_dir)).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(btn_frame, text="📦 Abrir Arquivos", command=lambda: self._open_folder(self.router.generic_downloader.output_dir)).pack(side=tk.RIGHT)

        # === Frame de Progresso ===
        self.progress_frame = ttk.Frame(self.root, padding=10)
        self.progress_frame.pack(fill=tk.X)
        
        self.status_lbl = ttk.Label(self.progress_frame, text="Aguardando URL...", font=('', 10))
        self.status_lbl.pack(fill=tk.X, pady=(0,5))
        
        self.type_status_lbl = ttk.Label(self.progress_frame, text="", font=('', 9), foreground="#666")
        self.type_status_lbl.pack(fill=tk.X, pady=(0,5))
        
        self.pct_lbl = ttk.Label(self.progress_frame, text="0%", anchor=tk.E, font=('', 10, 'bold'))
        self.pct_lbl.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(5,0))

        # === Frame de Histórico ===
        self.hist_frame = ttk.Frame(self.root, padding=(10,10,10,5))
        self.hist_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.hist_frame, text="📋 Histórico de Downloads:").pack(anchor=tk.W)
        
        self.hist_list = tk.Listbox(self.hist_frame, height=5, font=('', 9))
        self.hist_list.pack(fill=tk.BOTH, expand=True, pady=5)
        
        hist_scroll = ttk.Scrollbar(self.hist_frame, command=self.hist_list.yview)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.hist_list.config(yscrollcommand=hist_scroll.set)
        
        ttk.Button(self.hist_frame, text="🗑️ Limpar Histórico", command=lambda: self.hist_list.delete(0, tk.END)).pack(anchor=tk.E)

        # === Frame de Logs ===
        self.log_frame = ttk.Frame(self.root, padding=(10,5,10,10))
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.log_frame, text="📜 Logs do Sistema:").pack(anchor=tk.W)
        
        self.log_text = tk.Text(self.log_frame, height=12, state=tk.DISABLED, 
                               font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        log_scroll = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Configura logging
        self.sys_logger = setup_logging(text_widget=self.log_text)
        self.sys_logger.info("🌟 Universal Downloader v4.0 inicializado.")
        self.sys_logger.info(f"📁 Logs: {LOG_FILE}")
        self.sys_logger.info(f"🎬 Videos: {os.path.abspath(self.router.video_downloader.output_dir)}")
        self.sys_logger.info(f"📄 Arquivos: {os.path.abspath(self.router.generic_downloader.output_dir)}")

        # Configura grid weights para responsividade
        self.input_frame.columnconfigure(0, weight=1)
        self.hist_frame.rowconfigure(1, weight=1)
        self.log_frame.rowconfigure(1, weight=1)

    def _detect_url_type(self):
        """Detecta e exibe o tipo da URL sem iniciar download"""
        url = self.url_var.get().strip()
        if not url:
            self.type_label.config(text="⚠️ Insira uma URL primeiro", foreground="#dc3545")
            return
        
        url_type = URLDetector.classify_url(url)
        
        if url_type == 'invalid':
            self.type_label.config(text="❌ URL inválida", foreground="#dc3545")
        elif url_type == 'video':
            self.type_label.config(text="🎬 Plataforma de vídeo detectada → pasta videos/", foreground="#0078d7")
        else:
            name, ext = URLDetector.extract_filename_from_url(url)
            self.type_label.config(text=f"📄 Arquivo genérico: {name}{ext} → pasta arquivos/", foreground="#28a745")
        
        self.sys_logger.info(f"🔍 Detecção manual: {url[:60]}... → {url_type}")

    def start_download(self):
        """Inicia o processo de download com roteamento automático"""
        url = self.url_var.get().strip()
        
        if not url:
            self.sys_logger.warning("⚠️ Tentativa de download com URL vazia.")
            messagebox.showwarning("Atenção", "Insira uma URL válida.")
            return
        
        if self.is_downloading:
            self.sys_logger.warning("⏳ Download já em andamento.")
            return

        # Classifica URL para feedback visual
        self.current_url_type = URLDetector.classify_url(url)
        if self.current_url_type == 'invalid':
            messagebox.showerror("URL Inválida", "Por favor, insira uma URL http:// ou https:// válida.")
            return

        # Prepara interface
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED, text="⏳ Processando...")
        self.url_entry.config(state=tk.DISABLED)
        self.detect_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.pct_lbl.config(text="0%")
        
        if self.current_url_type == 'video':
            self.status_lbl.config(text="🎬 Conectando à plataforma de vídeo...")
            self.type_status_lbl.config(text="Backend: yt-dlp | Destino: videos/")
        else:
            self.status_lbl.config(text="📄 Conectando ao servidor...")
            self.type_status_lbl.config(text="Backend: requests | Destino: arquivos/")
        
        self.sys_logger.info(f"👤 Usuário solicitou download [{self.current_url_type}]: {url}")

        # Inicia thread
        thread = threading.Thread(target=self._run_download, args=(url,), daemon=True)
        thread.start()

    def _run_download(self, url):
        """Thread worker que executa o download via router"""
        
        def on_progress(pct):
            self.root.after(0, lambda: self._update_progress(pct))

        def on_complete(name, path, dtype):
            self.root.after(0, lambda: self._finish_download(name, path, dtype))

        def on_error(msg):
            self.root.after(0, lambda: self._handle_error(msg))

        self.router.download(url, on_progress, on_complete, on_error)

    def _update_progress(self, pct):
        """Atualiza indicadores de progresso na UI"""
        self.progress_bar['value'] = pct
        self.pct_lbl.config(text=f"{pct}%")
        if pct < 100:
            self.status_lbl.config(text=f"Baixando... {pct}%")

    def _finish_download(self, name, path, dtype):
        """Finaliza download com sucesso"""
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="⬇️ Baixar")
        self.url_entry.config(state=tk.NORMAL)
        self.detect_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="✅ Concluído!")
        self.pct_lbl.config(text="100%")
        
        # Adiciona ao histórico com ícone e tipo
        icon = "🎬" if dtype == 'video' else "📄"
        folder = "videos" if dtype == 'video' else "arquivos"
        display = f"{icon} [{folder}] {name[:45]}{'...' if len(name)>45 else ''}"
        self.hist_list.insert(tk.END, display)
        self.hist_list.yview_moveto(1)
        
        self.sys_logger.info(f"🎉 Download [{dtype}] finalizado: {Path(path).name}")
        
        # Mensagem contextual
        messagebox.showinfo(
            "Download Concluído", 
            f"{icon} Arquivo salvo com sucesso!\n\n"
            f"Nome: {name}\n"
            f"Pasta: {folder}/\n"
            f"Caminho: {path}"
        )

    def _handle_error(self, msg):
        """Trata erro durante o download"""
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="⬇️ Baixar")
        self.url_entry.config(state=tk.NORMAL)
        self.detect_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="❌ Falha no download")
        self.type_status_lbl.config(text="")
        
        self.sys_logger.error(f"🚨 Processo interrompido: {msg}")
        messagebox.showerror("Erro no Download", f"Não foi possível concluir o download:\n\n{msg}")

    def _configure_folders(self):
        """Permite configurar pastas de destino para vídeos e arquivos"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configurar Pastas")
        config_window.geometry("400x250")
        config_window.transient(self.root)
        config_window.grab_set()
        
        ttk.Label(config_window, text="📁 Configurar Diretórios de Download", font=('', 11, 'bold')).pack(pady=10)
        
        # Video folder
        video_frame = ttk.Frame(config_window, padding=5)
        video_frame.pack(fill=tk.X, padx=20)
        ttk.Label(video_frame, text="🎬 Pasta de Vídeos:").pack(anchor=tk.W)
        video_var = tk.StringVar(value=self.router.video_downloader.output_dir)
        ttk.Entry(video_frame, textvariable=video_var, width=40, state='readonly').pack(fill=tk.X, pady=(0,5))
        ttk.Button(video_frame, text="Alterar...", 
                  command=lambda: self._select_folder_dialog(video_var, "videos")).pack(anchor=tk.E)
        
        # Generic folder
        generic_frame = ttk.Frame(config_window, padding=5)
        generic_frame.pack(fill=tk.X, padx=20)
        ttk.Label(generic_frame, text="📄 Pasta de Arquivos:").pack(anchor=tk.W)
        generic_var = tk.StringVar(value=self.router.generic_downloader.output_dir)
        ttk.Entry(generic_frame, textvariable=generic_var, width=40, state='readonly').pack(fill=tk.X, pady=(0,5))
        ttk.Button(generic_frame, text="Alterar...", 
                  command=lambda: self._select_folder_dialog(generic_var, "arquivos")).pack(anchor=tk.E)
        
        # Save button
        def save_config():
            self.router.set_output_dirs(video_var.get(), generic_var.get())
            self.sys_logger.info(f"⚙️ Pastas atualizadas: videos={video_var.get()}, arquivos={generic_var.get()}")
            messagebox.showinfo("Configuração", "Pastas atualizadas com sucesso!", parent=config_window)
            config_window.destroy()
        
        ttk.Button(config_window, text="💾 Salvar Configurações", command=save_config).pack(pady=15)

    def _select_folder_dialog(self, string_var: tk.StringVar, default_name: str):
        """Abre dialog para seleção de pasta"""
        folder = filedialog.askdirectory(
            title=f"Selecionar pasta para {default_name}",
            initialdir=string_var.get()
        )
        if folder:
            string_var.set(folder)

    def _open_folder(self, path):
        """Abre pasta no explorador de arquivos do sistema"""
        path = os.path.abspath(path)
        if os.path.exists(path):
            try:
                os.startfile(path)  # Windows
            except AttributeError:
                os.system(f'open "{path}"')  # macOS
            except:
                os.system(f'xdg-open "{path}"')  # Linux
        else:
            messagebox.showerror("Erro", f"Pasta não encontrada:\n{path}")

# ==================== PONTO DE ENTRADA ====================

def main():
    root = tk.Tk()
    
    # Configuração de ícone cross-platform
    try:
        root.iconbitmap(default='')
    except tk.TclError:
        try:
            empty_icon = tk.PhotoImage(width=1, height=1)
            root.iconphoto(True, empty_icon)
        except:
            pass
    
    # Cria e executa aplicação
    app = MainWindow(root)
    
    # Centraliza janela
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")
    
    # Handler de fechamento
    def on_closing():
        if messagebox.askokcancel("Sair", "Deseja realmente encerrar o Universal Downloader?"):
            app.sys_logger.info("👋 Aplicação encerrada pelo usuário.")
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()