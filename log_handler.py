import logging
import tkinter as tk
import os
from datetime import datetime
import sys

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