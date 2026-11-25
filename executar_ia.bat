@echo off
:: Move para a pasta onde o arquivo .bat esta localizado (agora C:\IA)
cd /d "%~dp0"

:: Fecha qualquer versão antiga do Python/Streamlit
taskkill /f /im python.exe /t >nul 2>&1

:: Inicia o Streamlit em modo "headless"
start /b py -3.12 -m streamlit run assistente.py --server.headless true --server.port 8501 --browser.gatherUsageStats false

:: Aguarda o servidor carregar
timeout /t 5 /nobreak >nul

set "URL=http://localhost:8501"
set "EDGE_PATH="
for /f "tokens=2*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe" /ve 2^>nul') do set "EDGE_PATH=%%b"
if not defined EDGE_PATH (
    for /f "tokens=2*" %%a in ('reg query "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe" /ve 2^>nul') do set "EDGE_PATH=%%b"
)

if defined EDGE_PATH (
    start "" "%EDGE_PATH%" --app=%URL%
) else (
    start msedge --app=%URL% || start "" "%URL%"
)