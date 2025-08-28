import os
import pandas as pd
import difflib
import requests
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from pyngrok import conf, ngrok
from datetime import datetime
import webbrowser
from plyer import notification
import tkinter as tk
from tkinter import messagebox, ttk
import threading

# ===== CONFIGURAÇÕES =====
PASTA_ARQUIVOS = "arquivos"
PASTA_DADOS = "dados"
PASTA_RECEBIDOS = "dados_recebidos"
PORTA = 5000

# Criar pastas se não existirem
for pasta in [PASTA_ARQUIVOS, PASTA_DADOS, PASTA_RECEBIDOS]:
    os.makedirs(pasta, exist_ok=True)

# Variáveis globais para tokens
NGROK_AUTH_TOKEN = ""

class ConfigWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Configuração do Sistema Chatbot")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        title_label = ttk.Label(main_frame, text="Configuração do Sistema Chatbot", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Ngrok Auth Token
        ttk.Label(main_frame, text="Ngrok Auth Token:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ngrok_entry = ttk.Entry(main_frame, width=40, show="*")
        self.ngrok_entry.grid(row=1, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
        
        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Iniciar Servidor", 
                  command=self.start_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpar Token", 
                  command=self.limpar_token).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Sair", 
                  command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Status: Aguardando configuração...", 
                                     font=("Arial", 9), foreground="blue")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Informação sobre token salvo
        self.token_info_label = ttk.Label(main_frame, text="", 
                                         font=("Arial", 8), foreground="gray")
        self.token_info_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Carregar configurações salvas se existirem
        self.load_saved_config()
        
    def load_saved_config(self):
        try:
            if os.path.exists("config.txt"):
                with open("config.txt", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("NGROK_AUTH_TOKEN="):
                            token = line.split("=")[1].strip()
                            self.ngrok_entry.insert(0, token)
                            # Mostrar que há um token salvo
                            if token:
                                self.token_info_label.config(
                                    text="✓ Token encontrado e carregado automaticamente",
                                    foreground="green"
                                )
                            break
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
            
    def save_config(self):
        try:
            with open("config.txt", "w") as f:
                token = self.ngrok_entry.get().strip()
                f.write(f"NGROK_AUTH_TOKEN={token}\n")
                
            # Atualizar informação do token
            if token:
                self.token_info_label.config(
                    text="✓ Token salvo com sucesso",
                    foreground="green"
                )
            else:
                self.token_info_label.config(
                    text="ℹ Nenhum token salvo",
                    foreground="blue"
                )
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configuração: {e}")
    
    def limpar_token(self):
        # Limpar campo de entrada
        self.ngrok_entry.delete(0, tk.END)
        
        # Tentar remover arquivo de configuração
        try:
            if os.path.exists("config.txt"):
                os.remove("config.txt")
                self.token_info_label.config(
                    text="✓ Token removido com sucesso",
                    foreground="green"
                )
                messagebox.showinfo("Sucesso", "Token removido com sucesso!")
            else:
                self.token_info_label.config(
                    text="ℹ Nenhum token estava salvo",
                    foreground="blue"
                )
                messagebox.showinfo("Informação", "Nenhum token estava salvo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao remover token: {e}")
    
    def start_server(self):
        global NGROK_AUTH_TOKEN
        
        NGROK_AUTH_TOKEN = self.ngrok_entry.get().strip()
        
        if not NGROK_AUTH_TOKEN:
            messagebox.showerror("Erro", "Por favor, preencha o token do Ngrok!")
            return
            
        # Salvar configuração
        self.save_config()
        
        # Configurar ngrok
        try:
            ngrok.set_auth_token(NGROK_AUTH_TOKEN)
            conf.get_default().ngrok_path = "ngrok.exe" if os.name == 'nt' else "ngrok"
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao configurar ngrok: {e}")
            return
            
        self.status_label.config(text="Status: Iniciando servidor...", foreground="green")
        
        # Iniciar servidor em thread separada
        server_thread = threading.Thread(target=self.run_flask_server, daemon=True)
        server_thread.start()
        
    def run_flask_server(self):
        # ===== FUNÇÃO DE NOTIFICAÇÃO =====
        def notificar(titulo, mensagem):
            try:
                notification.notify(
                    title=titulo,
                    message=mensagem,
                    timeout=5
                )
            except:
                pass

        # ===== CHATBOT =====
        def responder_pergunta(pergunta):
            pergunta_original = pergunta.strip()
            pergunta_lower = pergunta_original.lower()
            todas_perguntas, perguntas_respostas = [], []
            resposta_final = ""

            for nome in os.listdir(PASTA_DADOS):
                if nome.endswith(".xlsx"):
                    caminho = os.path.join(PASTA_DADOS, nome)
                    try:
                        df = pd.read_excel(caminho)
                        if df.shape[1] < 2:
                            continue
                        perguntas = df.iloc[:, 0].astype(str).str.lower().tolist()
                        respostas = df.iloc[:, 1].astype(str).tolist()
                        todas_perguntas.extend(perguntas)
                        perguntas_respostas.extend(zip(perguntas, respostas))
                    except:
                        continue

            match = difflib.get_close_matches(pergunta_lower, todas_perguntas, n=1, cutoff=0.6)
            if match:
                for p, r in perguntas_respostas:
                    if p == match[0]:
                        resposta_final = r
                        break
            else:
                sugestoes = difflib.get_close_matches(pergunta_lower, todas_perguntas, n=3, cutoff=0.4)
                if sugestoes:
                    resposta_final = f"❓ Não encontrei uma resposta exata.\nTalvez você quis dizer:\n• " + "\n• ".join(sugestoes)
                else:
                    resposta_final = "❌ Desculpa, não encontrei nenhuma resposta relacionada."

            # Log
            with open(os.path.join(PASTA_RECEBIDOS, "conversas_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"❓ Pergunta: {pergunta_original}\n")
                f.write(f"💬 Resposta: {resposta_final}\n---\n")

            # Notificação
            notificar("🤖 Chatbot", f"Nova pergunta: {pergunta_original}")

            return resposta_final

        # ===== FLASK APP =====
        app = Flask(__name__)

        @app.route('/', methods=['GET', 'POST'])
        def index():
            arquivos = sorted([f for f in os.listdir(PASTA_ARQUIVOS) if os.path.isfile(os.path.join(PASTA_ARQUIVOS, f))])
            resposta = None
            if request.method == 'POST' and 'mensagem' in request.form:
                resposta = responder_pergunta(request.form.get('mensagem'))
            return render_template('index.html', arquivos=arquivos, resposta=resposta)

        @app.route('/upload', methods=['POST'])
        def upload():
            nome = request.form.get("nome")
            contacto = request.form.get("contacto")
            comentario = request.form.get("comentario")
            arquivo = request.files['arquivo']

            if arquivo:
                nome_arquivo = secure_filename(arquivo.filename)
                caminho = os.path.join(PASTA_RECEBIDOS, nome_arquivo)
                arquivo.save(caminho)

                with open(os.path.join(PASTA_RECEBIDOS, "envios_log.txt"), "a", encoding="utf-8") as f:
                    f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Nome: {nome}\nContato: {contacto}\nComentário: {comentario}\nArquivo: {nome_arquivo}\n---\n")

                # Notificação
                notificar("📥 Upload Recebido", f"Arquivo: {nome_arquivo}\nEnviado por: {nome}")

            return redirect(url_for('index'))

        @app.route('/download/<nome_arquivo>')
        def download(nome_arquivo):
            return send_from_directory(PASTA_ARQUIVOS, nome_arquivo, as_attachment=True)

        @app.route('/arquivos/<nome_arquivo>')
        def arquivos_static(nome_arquivo):
            return send_from_directory(PASTA_ARQUIVOS, nome_arquivo)

        @app.route('/feedback', methods=['POST'])
        def feedback():
            encarregado = request.form.get("encarregado")
            aluno = request.form.get("aluno")
            contacto = request.form.get("contacto")
            mensagem = request.form.get("mensagem")

            with open(os.path.join(PASTA_RECEBIDOS, "feedback_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"👤 Encarregado: {encarregado}\n")
                f.write(f"🎓 Aluno: {aluno}\n")
                f.write(f"☎️ Contacto: {contacto}\n")
                f.write(f"💬 Reclamação/Sugestão: {mensagem}\n---\n")

            # Notificação
            notificar("📢 Feedback Recebido", f"{encarregado} enviou uma mensagem.")

            return redirect(url_for('index'))

        # Inicia ngrok com HTTPS
        try:
            public_url = ngrok.connect(PORTA, bind_tls=True).public_url
            print(f"🔗 Link ngrok (HTTPS): {public_url}")
            
            # Atualizar interface
            self.root.after(0, lambda: self.status_label.config(
                text=f"Status: Servidor rodando!\nURL: {public_url}", 
                foreground="green"
            ))

            # Abrir no navegador
            webbrowser.open(public_url)

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text=f"Erro: {str(e)}", 
                foreground="red"
            ))
            return

        # Executa Flask
        app.run(host="0.0.0.0", port=PORTA, debug=False, use_reloader=False)

def main():
    root = tk.Tk()
    app = ConfigWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()

