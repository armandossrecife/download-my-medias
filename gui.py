import logging
import os
from log_handler import LOG_FILE
from download_handler import DownloadRouter
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from log_handler import setup_logging
from utils import URLDetector
import threading
from pathlib import Path

# ==================== INTERFACE GRÁFICA ====================

class MainWindow:
    def __init__(self, root, title="Universal Downloader v4.1"):
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
        self.sys_logger.info("🌟 Universal Downloader v4.1 inicializado.")
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
