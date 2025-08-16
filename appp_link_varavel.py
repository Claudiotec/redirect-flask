import os
import pandas as pd
import difflib
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from pyngrok import conf, ngrok
import webbrowser
from datetime import datetime

# Caminho para o ngrok.exe
conf.get_default().ngrok_path = "ngrok.exe"

app = Flask(__name__)

PASTA_ARQUIVOS = "arquivos"
PASTA_DADOS = "dados"
PASTA_RECEBIDOS = "dados_recebidos"
PORTA = 5000

# Criar as pastas se não existirem
for pasta in [PASTA_ARQUIVOS, PASTA_DADOS, PASTA_RECEBIDOS]:
    os.makedirs(pasta, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    arquivos = os.listdir(PASTA_ARQUIVOS)
    arquivos = [f for f in arquivos if os.path.isfile(os.path.join(PASTA_ARQUIVOS, f))]
    resposta = None

    if request.method == 'POST' and 'mensagem' in request.form:
        mensagem = request.form.get('mensagem')
        resposta = responder_pergunta(mensagem)

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

        # Log de upload
        with open(os.path.join(PASTA_RECEBIDOS, "envios_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nome: {nome}\nContato: {contacto}\nComentário: {comentario}\nArquivo: {nome_arquivo}\n---\n")

    return redirect(url_for('index'))

@app.route('/download/<nome_arquivo>')
def download(nome_arquivo):
    return send_from_directory(PASTA_ARQUIVOS, nome_arquivo, as_attachment=True)

@app.route('/preview/<nome_arquivo>')
def preview(nome_arquivo):
    return send_from_directory(PASTA_ARQUIVOS, nome_arquivo)

# 💬 Função de resposta do chatbot com sugestão e log
def responder_pergunta(pergunta):
    pergunta_original = pergunta.strip()
    pergunta = pergunta_original.lower()
    todas_perguntas = []
    perguntas_respostas = []
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

    # Busca por similaridade
    match = difflib.get_close_matches(pergunta, todas_perguntas, n=1, cutoff=0.6)
    if match:
        for p, r in perguntas_respostas:
            if p == match[0]:
                resposta_final = r
                break
    else:
        # Sugestões
        sugestoes = difflib.get_close_matches(pergunta, todas_perguntas, n=3, cutoff=0.4)
        if sugestoes:
            sugestoes_formatadas = "\n• " + "\n• ".join(sugestoes)
            resposta_final = f"❓ Não encontrei uma resposta exata.\nTalvez você quis dizer:{sugestoes_formatadas}"
        else:
            resposta_final = "❌ Desculpa, não encontrei nenhuma resposta relacionada."

    # Log da conversa
    try:
        with open(os.path.join(PASTA_RECEBIDOS, "conversas_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"❓ Pergunta: {pergunta_original}\n")
            f.write(f"💬 Resposta: {resposta_final}\n---\n")
    except Exception as erro:
        print(f"[ERRO] Falha ao salvar conversa: {erro}")

    return resposta_final

if __name__ == '__main__':
    public_url = ngrok.connect(PORTA, bind_tls=True)
    print(f"🔗 Link real do sistema: {public_url.public_url}")
    print(f"🌐 Link visual (personalizado): https://claudtec.inovacao.com")
    webbrowser.open(public_url.public_url)
    app.run(port=PORTA)
