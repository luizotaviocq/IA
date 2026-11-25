import os
import sys
import time
import subprocess
import threading
import webbrowser

def log_debug(mensagem):
    """Salva mensagens em um arquivo para sabermos se o script está vivo"""
    dir_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_log = os.path.join(dir_atual, "debug_monitor.txt")
    timestamp = time.strftime("%H:%M:%S")
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {mensagem}\n")

try:
    import speech_recognition as sr
    import pyaudio
except Exception as e:
    # Se falhar nas bibliotecas, cria o log imediatamente relatando o erro
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_monitor.txt"), "a", encoding="utf-8") as f:
        print(f"Erro Crítico: {e}")
        print(f"Execute: {sys.executable} -m pip install speechrecognition pyaudio")
        f.write(f"[{time.strftime('%H:%M:%S')}] ERRO CRÍTICO DE DEPENDÊNCIA: {e}\n")
        f.write(f"DICA: Execute '{sys.executable} -m pip install speechrecognition pyaudio' no terminal.\n")
    sys.exit(1)

# Obtém o caminho absoluto para o arquivo assistente.py no mesmo diretório
diretorio = os.path.dirname(os.path.abspath(__file__))
caminho_assistente = os.path.join(diretorio, "assistente.py")

def iniciar_servidor_streamlit():
    """Inicia o servidor Streamlit em modo headless (sem abrir navegador)"""
    # Flags para desatachar o processo e esconder a janela (Windows)
    # 0x00000008 = DETACHED_PROCESS
    # 0x08000000 = CREATE_NO_WINDOW
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", caminho_assistente, "--server.headless", "true", "--server.port", "8501"],
        creationflags=subprocess.CREATE_NO_WINDOW | 0x00000008,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        cwd=diretorio
    )

def monitor_vocal():
    """Fica ouvindo o microfone em segundo plano"""
    rec = sr.Recognizer()
    rec.energy_threshold = 400  # Aumentado para evitar ruídos bobos
    rec.dynamic_energy_threshold = True
    
    log_debug("Monitor vocal iniciado. Aguardando 'fala L4M'...")
    
    # Loop infinito de escuta
    while True:
        try:
            with sr.Microphone() as source:
                # Ajuste rápido para o ruído ambiente a cada iteração
                rec.adjust_for_ambient_noise(source, duration=0.5)
                audio = rec.listen(source, phrase_time_limit=4, timeout=None)
                texto = rec.recognize_google(audio, language="pt-BR").lower()
                log_debug(f"Ouvi: {texto}")
                
                # Se detectar a palavra-chave, abre o navegador
                palavras_chave = ["fala l4m", "fala lfm", "fala l 4 m", "fala l 4m", "fala ele 4m", "fala assistente", "fala l4"]
                if any(pc in texto for pc in palavras_chave):
                    log_debug("Palavra de ativação detectada! Abrindo navegador...")
                    webbrowser.open("http://localhost:8501/?mic=true")
                    time.sleep(5)
        except sr.UnknownValueError:
            continue # Não entendeu nada, ignora
        except Exception as e:
            log_debug(f"Erro no monitor: {e}")
            time.sleep(2)

if __name__ == "__main__":
    # Limpa log antigo
    if os.path.exists(os.path.join(diretorio, "debug_monitor.txt")):
        os.remove(os.path.join(diretorio, "debug_monitor.txt"))

    log_debug("Iniciando processo principal...")
    # 1. Inicia o Streamlit
    iniciar_servidor_streamlit()
    log_debug("Servidor Streamlit disparado em segundo plano.")

    # 2. Inicia o monitor vocal no processo principal
    monitor_vocal()
