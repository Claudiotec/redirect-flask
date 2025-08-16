import os
import pandas as pd
import difflib
import requests
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from pyngrok import conf, ngrok
import webbrowser
from datetime import datetime

# ===== CONFIGURAÇÕES =====
conf.get_default().ngrok_path = "ngrok.exe"
DUCKDNS_DOMAIN = "claudtec"  # seu subdomínio no DuckDNS
DUCKDNS_TOKEN = "745aab66-6b4b-4c2c-a9f0-d34c9922d3d2"  # token do site do DuckDNS

PASTA_ARQUIVOS = "arquivos"
PASTA_DADOS = "dados"
PASTA_RECEBIDOS = "dados_recebidos"
PORTA = 5000

app = Flask(__name__)

# Criar pastas
for pasta in [PASTA_ARQUIVOS, PASTA_DADOS, PASTA_RECEBIDOS]:
    os.makedirs(pasta, exist_ok=True)

# ===== FUNÇÃO ATUALIZAR DUCKDNS =====
def atualizar_duckdns():
    try:
        url = f"https://www.duckdns.org/update?domains={DUCKDNS_DOMAIN}&token={DUCKDNS_TOKEN}&ip="
        r = requests.get(url)
        if "OK" in r.text.upper():
            print(f"✅ DuckDNS atualizado para {DUCKDNS_DOMAIN}.duckdns.org")
        else:
            print(f"⚠ Erro ao atualizar DuckDNS: {r.text}")
    except Exception as e:
        print(f"❌ Falha ao atualizar DuckDNS: {e}")

# ===== CHATBOT =====
def responder_pergunta(pergunta):
    pergunta_original = pergunta.strip()
    pergunta_lower = pergunta_original.lower()
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

    match = difflib.get_close_matches(pergunta_lower, todas_perguntas, n=1, cutoff=0.6)
    if match:
        for p, r in perguntas_respostas:
            if p == match[0]:
                resposta_final = r
                break
    else:
        sugestoes = difflib.get_close_matches(pergunta_lower, todas_perguntas, n=3, cutoff=0.4)
        if sugestoes:
            sugestoes_formatadas = "\n• " + "\n• ".join(sugestoes)
            resposta_final = f"❓ Não encontrei uma resposta exata.\nTalvez você quis dizer:{sugestoes_formatadas}"
        else:
            resposta_final = "❌ Desculpa, não encontrei nenhuma resposta relacionada."

    with open(os.path.join(PASTA_RECEBIDOS, "conversas_log.txt"), "a", encoding="utf-8") as f:
        f.write(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"❓ Pergunta: {pergunta_original}\n")
        f.write(f"💬 Resposta: {resposta_final}\n---\n")

    return resposta_final

# ===== ROTAS =====
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

    return redirect(url_for('index'))

@app.route('/download/<nome_arquivo>')
def download(nome_arquivo):
    return send_from_directory(PASTA_ARQUIVOS, nome_arquivo, as_attachment=True)

@app.route('/preview/<nome_arquivo>')
def preview(nome_arquivo):
    return send_from_directory(PASTA_ARQUIVOS, nome_arquivo)

# ===== INÍCIO =====
if __name__ == '__main__':
    public_url = ngrok.connect(PORTA, bind_tls=True)
    print(f"🔗 Link ngrok: {public_url.public_url}")

    atualizar_duckdns()  # Atualiza DuckDNS sempre que iniciar

    webbrowser.open(public_url.public_url)
    app.run(port=PORTA)
