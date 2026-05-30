"""
Universal Downloader - YouTube + Arquivos Genéricos
Versão: 4.1
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
from tkinter import messagebox
from gui import MainWindow

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