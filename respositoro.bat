@echo off
echo ================================
echo 🚀 Subindo projeto pro GitHub...
echo ================================

:: CONFIGURA NOME E EMAIL
git config --global user.name "Claudiotec"
git config --global user.email "teuemail@exemplo.com"

:: INICIALIZA O REPO
git init

:: ADICIONA ARQUIVOS
git add .

:: FAZ O COMMIT
git commit -m "primeiro commit"

:: GARANTE QUE ESTA NA BRANCH MAIN
git branch -M main

:: ADICIONA O REMOTO (só se não existir ainda)
git remote remove origin 2>nul
git remote add origin https://github.com/Claudiotec/redirect-flask.git

:: ENVIA PARA O GITHUB
git push -u origin main

pause
