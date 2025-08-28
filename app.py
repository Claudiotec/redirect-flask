import os
import pandas as pd
import difflib
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from plyer import notification

# ===== CONFIGURAÇÕES =====
PASTA_ARQUIVOS = "arquivos"
PASTA_DADOS = "dados"
PASTA_RECEBIDOS = "dados_recebidos"

# Obter porta do ambiente (Render define isso automaticamente)
PORT = int(os.environ.get("PORT", 5000))

# Criar pastas se não existirem
for pasta in [PASTA_ARQUIVOS, PASTA_DADOS, PASTA_RECEBIDOS]:
    os.makedirs(pasta, exist_ok=True)

# ===== FUNÇÃO DE NOTIFICAÇÃO =====
def notificar(titulo, mensagem):
    try:
        notification.notify(
            title=titulo,
            message=mensagem,
            timeout=5
        )
    except:
        pass  # Notificações podem não funcionar no Render

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
            except Exception as e:
                print(f"Erro ao ler arquivo {nome}: {e}")
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

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
