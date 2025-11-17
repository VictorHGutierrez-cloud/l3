#!/usr/bin/env python3
"""
GUI para Processar Transcrições Factorial
Interface gráfica simples para usar o extrator de tarefas
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path

# Adiciona o diretório atual ao path para importar o módulo
if getattr(sys, 'frozen', False):
    # Se está rodando como .exe (PyInstaller)
    base_path = sys._MEIPASS
    # Adiciona também o diretório do executável (onde pode estar o módulo)
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    # Se está rodando como script normal
    base_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_path)

try:
    from mcp_tarefas_factorial import processar_transcricao, enviar_email_tarefas, criar_eventos_calendario
except ImportError as e:
    # Tenta importar de forma mais flexível
    import importlib.util
    module_path = os.path.join(base_path, 'mcp_tarefas_factorial.py')
    if os.path.exists(module_path):
        spec = importlib.util.spec_from_file_location("mcp_tarefas_factorial", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        processar_transcricao = module.processar_transcricao
        enviar_email_tarefas = module.enviar_email_tarefas
        criar_eventos_calendario = module.criar_eventos_calendario
    else:
        import tkinter.messagebox as messagebox
        messagebox.showerror(
            "Erro de Importação",
            f"Não foi possível importar o módulo mcp_tarefas_factorial.py\n\n"
            f"Erro: {str(e)}\n\n"
            f"Certifique-se de que o arquivo está na mesma pasta do executável."
        )
        sys.exit(1)


class AppTarefas:
    def __init__(self, root):
        self.root = root
        self.root.title("📋 Processador de Transcrições Factorial")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variáveis
        self.arquivo_selecionado = None
        
        # Cria interface
        self.criar_interface()
    
    def criar_interface(self):
        """Cria todos os elementos da interface"""
        
        # Título
        titulo = tk.Label(
            self.root,
            text="📋 Processador de Transcrições Factorial",
            font=("Arial", 16, "bold"),
            pady=10
        )
        titulo.pack()
        
        # Frame para seleção de arquivo
        frame_arquivo = tk.Frame(self.root, pady=10)
        frame_arquivo.pack(fill=tk.X, padx=20)
        
        tk.Label(
            frame_arquivo,
            text="Arquivo de Transcrição:",
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.label_arquivo = tk.Label(
            frame_arquivo,
            text="Nenhum arquivo selecionado",
            fg="gray",
            font=("Arial", 9)
        )
        self.label_arquivo.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        
        btn_selecionar = tk.Button(
            frame_arquivo,
            text="📁 Selecionar Arquivo",
            command=self.selecionar_arquivo,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=5
        )
        btn_selecionar.pack(side=tk.RIGHT)
        
        # Botão Processar
        self.btn_processar = tk.Button(
            self.root,
            text="🚀 Processar Transcrição",
            command=self.processar_arquivo,
            bg="#2196F3",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10,
            state=tk.DISABLED
        )
        self.btn_processar.pack(pady=10)
        
        # Área de log
        tk.Label(
            self.root,
            text="Log de Processamento:",
            font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, padx=20, pady=(10, 5))
        
        self.text_log = scrolledtext.ScrolledText(
            self.root,
            height=20,
            font=("Consolas", 9),
            bg="#f5f5f5",
            wrap=tk.WORD
        )
        self.text_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Pronto",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def selecionar_arquivo(self):
        """Abre diálogo para selecionar arquivo"""
        arquivo = filedialog.askopenfilename(
            title="Selecione o arquivo de transcrição",
            filetypes=[
                ("Arquivos de texto", "*.txt"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if arquivo:
            self.arquivo_selecionado = arquivo
            nome_arquivo = os.path.basename(arquivo)
            self.label_arquivo.config(text=nome_arquivo, fg="black")
            self.btn_processar.config(state=tk.NORMAL)
            self.log(f"✅ Arquivo selecionado: {nome_arquivo}")
    
    def log(self, mensagem):
        """Adiciona mensagem ao log"""
        self.text_log.insert(tk.END, mensagem + "\n")
        self.text_log.see(tk.END)
        self.root.update()
    
    def atualizar_status(self, texto):
        """Atualiza a barra de status"""
        self.status_bar.config(text=texto)
        self.root.update()
    
    def processar_arquivo(self):
        """Processa o arquivo selecionado"""
        if not self.arquivo_selecionado:
            messagebox.showwarning("Aviso", "Por favor, selecione um arquivo primeiro.")
            return
        
        # Desabilita botão durante processamento
        self.btn_processar.config(state=tk.DISABLED)
        self.text_log.delete(1.0, tk.END)
        
        # Processa em thread separada para não travar a interface
        thread = threading.Thread(target=self.executar_processamento)
        thread.daemon = True
        thread.start()
    
    def executar_processamento(self):
        """Executa o processamento (em thread separada)"""
        try:
            self.log("=" * 60)
            self.log("📋 PROCESSANDO TRANSCRIÇÃO")
            self.log("=" * 60)
            self.log("")
            
            # Lê arquivo
            self.atualizar_status("Lendo arquivo...")
            self.log(f"📁 Lendo arquivo: {os.path.basename(self.arquivo_selecionado)}")
            
            with open(self.arquivo_selecionado, 'r', encoding='utf-8') as f:
                texto = f.read()
            
            self.log(f"✅ Arquivo lido com sucesso! ({len(texto)} caracteres)")
            self.log("")
            
            # Processa transcrição
            self.atualizar_status("Extraindo tarefas...")
            self.log("🔍 Analisando transcrição e extraindo tarefas...")
            self.log("")
            
            resultado = processar_transcricao(texto)
            
            self.log("=" * 60)
            self.log(f"✅ RESUMO: {resultado['total']} tarefa(s) encontrada(s)")
            self.log(f"   ⏰ {resultado['com_deadline']} com deadline")
            self.log(f"   📝 {resultado['sem_deadline']} sem deadline")
            self.log("=" * 60)
            self.log("")
            
            # Mostra tarefas
            if resultado['tarefas']:
                self.log("📝 TAREFAS IDENTIFICADAS:")
                self.log("-" * 60)
                for i, tarefa in enumerate(resultado['tarefas'], 1):
                    self.log(f"\n{i}. {tarefa['texto']}")
                    if tarefa.get('deadline'):
                        d = tarefa['deadline']
                        horario = f" às {d['horario']}" if d.get('horario') else ""
                        self.log(f"   ⏰ Deadline: {d['data']}{horario} ({d['texto_original']})")
                    if tarefa.get('contexto'):
                        self.log(f"   💬 Contexto: {tarefa['contexto'][:80]}...")
                self.log("")
                
                # Envia email
                self.atualizar_status("Enviando email...")
                self.log("📧 Enviando email para victor.gutierrez@factorial.co...")
                email_result = enviar_email_tarefas(resultado['tarefas'])
                
                if email_result.get('sucesso'):
                    self.log(f"✅ {email_result.get('mensagem')}")
                else:
                    self.log(f"⚠️  Erro ao enviar email: {email_result.get('erro')}")
                self.log("")
                
                # Cria eventos no calendário
                tarefas_com_deadline = [t for t in resultado['tarefas'] if t.get('deadline')]
                if tarefas_com_deadline:
                    self.atualizar_status("Criando eventos no calendário...")
                    self.log("📅 Criando eventos no Google Calendar...")
                    calendario_result = criar_eventos_calendario(tarefas_com_deadline)
                    
                    if calendario_result.get('sucesso'):
                        self.log(f"✅ {calendario_result.get('mensagem')}")
                    else:
                        self.log(f"⚠️  {calendario_result.get('erro')}")
                        if 'não configuradas' in calendario_result.get('erro', '').lower():
                            self.log("💡 Execute 'configurar_google_calendar.py' para configurar o calendário")
                    self.log("")
            else:
                self.log("ℹ️  Nenhuma tarefa encontrada na transcrição.")
                self.log("")
            
            self.log("=" * 60)
            self.log("✅ PROCESSO CONCLUÍDO!")
            self.log("=" * 60)
            
            self.atualizar_status("Processamento concluído!")
            
            # Mostra mensagem de sucesso
            self.root.after(0, lambda: messagebox.showinfo(
                "Sucesso",
                f"Processamento concluído!\n\n"
                f"Total de tarefas: {resultado['total']}\n"
                f"Com deadline: {resultado['com_deadline']}\n"
                f"Sem deadline: {resultado['sem_deadline']}"
            ))
            
            # Reabilita botão
            self.root.after(0, lambda: self.btn_processar.config(state=tk.NORMAL))
            
        except FileNotFoundError:
            self.log(f"❌ ERRO: Arquivo não encontrado!")
            self.atualizar_status("Erro: arquivo não encontrado")
            self.root.after(0, lambda: messagebox.showerror(
                "Erro",
                "Arquivo não encontrado!"
            ))
            self.root.after(0, lambda: self.btn_processar.config(state=tk.NORMAL))
        
        except Exception as e:
            self.log(f"❌ ERRO: {str(e)}")
            self.atualizar_status(f"Erro: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror(
                "Erro",
                f"Ocorreu um erro:\n\n{str(e)}"
            ))
            self.root.after(0, lambda: self.btn_processar.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    app = AppTarefas(root)
    root.mainloop()


if __name__ == "__main__":
    main()