import os
import re
import subprocess
import time
import base64
import webbrowser
import uuid
import sqlite3
import requests
import threading
import pyttsx3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import hashlib
import tempfile
import speech_recognition as sr
from PIL import Image
import streamlit as st
import psutil
from crewai import Agent, Task, Crew, LLM
from tools import (
    abrir_aplicativo_windows, fechar_aplicativo_windows, buscar_arquivo_computador,
    pesquisar_google, abrir_google_no_navegador, ler_conteudo_arquivo,
    analisar_imagem, digitar_texto_no_pc, pressionar_teclas_atalho, obter_data_hora,
    executar_calculo_matematico, focar_janela_windows
)

# --- CONFIGURAÇÃO DE IMAGEM ---
# Agora o código busca a imagem na mesma pasta do script automaticamente
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

def encontrar_foto_perfil():
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        caminho = os.path.join(diretorio_atual, f"avatar{ext}")
        if os.path.exists(caminho):
            return caminho
    return None

FOTO_PERFIL = encontrar_foto_perfil()

DB_FOLDER = os.path.join(diretorio_atual, "database")
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

HISTORY_DB = os.path.join(DB_FOLDER, "chat_history.db")
USERS_DB = os.path.join(DB_FOLDER, "users.db")

# Configuração da página do Streamlit
st.set_page_config(page_title="L4M - Assistente de Sistema", page_icon=FOTO_PERFIL if FOTO_PERFIL else "🤖", initial_sidebar_state="expanded")
st.title("🤖 L4M")
st.markdown("Controle seu PC através de conversa natural.")

# O monitor vocal agora é gerenciado pelo script de inicialização (ligar_L4M.py)
# para permitir que o assistente seja chamado mesmo com o navegador fechado.

# --- ESTILO NATIVO (Esconder menus do Streamlit) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {padding-top: 1rem;}
    </style>
""", unsafe_allow_html=True)

# 1. Configurar o Ollama direto pelo padrão do CrewAI
o_seu_ollama = LLM(
    model="ollama/llama3.1",
    base_url="http://localhost:11434",
    temperature=0.1
)

# 3. Definir o Agente
controlador_pc = Agent(
    role='L4M',
    goal='Agente de execução imediata. Sua missão é manipular o Windows conforme solicitado e confirmar a ação.',
    backstory="""Você é o L4M, um assistente prático e direto para Windows. 
    Você é um assistente pessoal versátil: além de controlar o PC, você informa o usuário sobre o mundo.
    
    INSTRUÇÕES:
    1. Se o usuário fizer uma PERGUNTA factual (ex: preços, clima, ciência, geografia, quem é tal pessoa), use a ferramenta 'pesquisar_google' para obter dados reais. Foque exatamente no que foi pedido (ex: se citar uma loja, pesquise nela).
    2. Só use 'abrir_google_no_navegador' se ele pedir explicitamente para "ver o site" ou "abrir a página".
    3. AUTOMAÇÃO DE MENSAGENS: Para mandar mensagens em apps, a sequência é: 1º Focar o app, 2º Usar 'pressionar_teclas_atalho' para busca (ex: 'ctrl, k' no Discord), 3º Digitar o contato e 4º Digitar a mensagem.
    4. RESPOSTA DE SUCESSO: Após realizar uma automação (abrir, digitar, enviar), sua resposta final deve ser APENAS uma confirmação curta (ex: 'Mensagem enviada'). NÃO repita o conteúdo da mensagem no chat.
    5. FOCO OBRIGATÓRIO: Sempre use 'focar_janela_windows' antes de digitar qualquer texto para garantir que o app alvo receba as teclas.
    5. Responda sempre em português, de forma direta e sem exibir formatos técnicos como JSON ou chaves {}.
    6. PESQUISA DE PREÇOS E FATOS: Seja persistente e específico. Se o usuário perguntar de uma loja (ex: Americanas), você deve procurar especificamente nela. Não repita informações de buscas anteriores se a nova pergunta for diferente.
    7. Corrija erros de fala do usuário silenciosamente.
    8. Se o pedido for apenas uma saudação ou conversa informal (ex: 'oi', 'olá', 'tudo bem'), responda de forma amigável SEM usar nenhuma ferramenta.
    9. NUNCA explique sua lógica interna e não repita os dados do prompt na resposta final.
    10. CITAÇÃO DE FONTES: SÓ cite a fonte ou o link se o usuário pedir explicitamente (ex: "qual a fonte?", "de onde veio isso?"). Caso contrário, forneça apenas a informação direta.
    11. PRIORIDADE DE RESPOSTA: O objetivo principal é informar o usuário. Se a pesquisa falhar, mas você souber a resposta (ex: fatos históricos ou científicos), responda com seu conhecimento e mencione que a informação é de conhecimento geral.
    12. Para cálculos ou conversões: pesquise o valor/taxa atual se necessário e use OBRIGATORIAMENTE 'executar_calculo_matematico' para o resultado final.""",
    verbose=True,
    llm=o_seu_ollama,
    tools=[abrir_aplicativo_windows, fechar_aplicativo_windows, buscar_arquivo_computador, pesquisar_google, abrir_google_no_navegador, ler_conteudo_arquivo, analisar_imagem, digitar_texto_no_pc, pressionar_teclas_atalho, obter_data_hora, executar_calculo_matematico, focar_janela_windows],
    allow_delegation=False,
    memory=False
)

# 4. Definir a tarefa com placeholders {pedido}
tarefa_abrir = Task(
    description=(
        "PEDIDO DO USUÁRIO: '{pedido}'\n"
        "Histórico: {historico}\n\n"
        "FLUXO DE TRABALHO:\n"
        "1. Se o pedido for uma automação (ex: mandar mensagem), execute a sequência de ferramentas e finalize a tarefa reportando APENAS o sucesso da ação.\n"
        "2. Se for apenas conversa, responda diretamente.\n"
        "3. PROIBIDO exibir metadados técnicos ou sua lógica de pensamento. Responda com o texto final de diálogo. Só inclua fontes se solicitado no pedido."
    ),
    expected_output="Uma confirmação curta do sucesso da automação ou a resposta textual à pergunta do usuário.",
    agent=controlador_pc
)

# --- FUNÇÕES DE VOZ ---

def falar_texto(texto):
    """Converte texto em fala."""
    if st.session_state.get("voice_active", False):
        choice = st.session_state.get("selected_voice_name")

        usou_ia = False
        if choice == "🎭 Voz de Personagem (ElevenLabs)":
            # --- VOZ DE PERSONAGEM (ElevenLabs) ---
            try:
                api_key = st.session_state.get("eleven_api_key")
                voice_id = st.session_state.get("eleven_voice_id")
                if not api_key or not voice_id: raise Exception("Configuração incompleta")
                
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key}
                data = {"text": texto, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    audio_base64 = base64.b64encode(response.content).decode('utf-8')
                    st.session_state.last_audio_base64 = audio_base64
                    st.session_state.last_audio_mime = "audio/mpeg"
                elif "free_users_not_allowed" in response.text:
                    st.error("Erro ElevenLabs: Esta voz exige conta paga (Tier Creator). Por favor, use uma voz gratuita da Voice Library.")
                else:
                    st.error(f"Erro ElevenLabs: {response.text}")
            except Exception as e:
                st.error(f"Falha na voz de IA: {e}")
        else:
            # --- VOZ DO SISTEMA (Offline) ---
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 200)
                
                v_id = st.session_state.get("selected_voice_id")
                if v_id:
                    engine.setProperty('voice', v_id)
                else:
                    for voice in engine.getProperty('voices'):
                        if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
                            engine.setProperty('voice', voice.id)
                            break

                # Para funcionar no browser via Streamlit, salvamos em arquivo e convertemos para base64
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
                    temp_path = tf.name
                
                engine.save_to_file(texto, temp_path)
                engine.runAndWait()
                engine.stop()
                
                with open(temp_path, "rb") as f:
                    st.session_state.last_audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                    st.session_state.last_audio_mime = "audio/wav"
                
                os.unlink(temp_path)
            except Exception as e:
                st.error(f"Erro na saída de voz do sistema: {e}")

# --- CLASSE PARA GRAVAÇÃO MANUAL (Controle total de Início/Fim) ---
class GravadorManual:
    def __init__(self):
        import pyaudio
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = True
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()

    def _record_loop(self):
        while self.is_recording:
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)
            except:
                break

    def parar(self):
        self.is_recording = False
        self.thread.join(timeout=2)
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        return b"".join(self.frames)

def ouvir_microfone():
    """Captura áudio do microfone e converte para texto."""
    r = sr.Recognizer()
    # Define o tempo de silêncio para fechar o mic (pedido: 5 segundos)
    r.pause_threshold = 5.0 
    r.dynamic_energy_threshold = True # Ajusta automaticamente à sensibilidade do ambiente
    
    try:
        with sr.Microphone() as source:
            st.toast("🎙️ Calibrando microfone...")
            # Reduzimos um pouco o tempo de calibração para ser mais rápido
            r.adjust_for_ambient_noise(source, duration=0.8)
            st.toast("🎙️ Pode falar! (Esperando 5s de silêncio)")
            
            audio = r.listen(source, timeout=10, phrase_time_limit=20)
            st.toast("⏳ Processando sua fala...")
            texto = r.recognize_google(audio, language="pt-BR")
            return texto
    except sr.WaitTimeoutError:
        st.toast("🛑 Tempo esgotado (ninguém falou).")
    except sr.UnknownValueError:
        st.toast("⚠️ Áudio não reconhecido.")
    except sr.RequestError:
        st.toast("🌐 Erro de conexão com serviço de voz.")
    except Exception as e:
        st.toast(f"❌ Erro no microfone: {str(e)}")
    return None

# 5. Criar a equipe uma única vez
equipe = Crew(
    agents=[controlador_pc],
    tasks=[tarefa_abrir],
    verbose=True,
    share_crew=False  # Desativa o compartilhamento de dados/telemetria
)

# --- BANCO DE DADOS (SQLite) ---

def init_db():
    """Inicializa o banco de dados e cria a tabela se não existir."""
    # --- BANCO DE HISTÓRICO E CONFIGURAÇÕES ---
    conn_h = sqlite3.connect(HISTORY_DB)
    cursor_h = conn_h.cursor()
    cursor_h.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT,
            role TEXT,
            content TEXT,
            image_data BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor_h.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Migrações History
    try:
        cursor_h.execute('ALTER TABLE history ADD COLUMN session_id TEXT')
        conn_h.commit()
        cursor_h.execute('UPDATE history SET session_id = "antigo" WHERE session_id IS NULL')
        conn_h.commit()
    except sqlite3.OperationalError: pass
    
    try:
        cursor_h.execute('ALTER TABLE history ADD COLUMN username TEXT')
        conn_h.commit()
    except sqlite3.OperationalError: pass
    
    try:
        cursor_h.execute('ALTER TABLE history ADD COLUMN image_data BLOB')
        conn_h.commit()
    except sqlite3.OperationalError: pass
    conn_h.close()

    # --- BANCO DE USUÁRIOS (CADASTROS) ---
    conn_u = sqlite3.connect(USERS_DB)
    cursor_u = conn_u.cursor()
    cursor_u.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            email TEXT,
            phone TEXT
        )
    ''')

    # Migrações para a tabela de usuários
    for col in ["full_name", "email", "phone"]:
        try:
            cursor_u.execute(f'ALTER TABLE users ADD COLUMN {col} TEXT')
        except sqlite3.OperationalError:
            pass

    conn_u.commit()
    conn_u.close()

def save_setting(key, value):
    """Salva uma configuração no banco de dados."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                   (key, value))
    conn.commit()
    conn.close()

def load_setting(key):
    """Carrega uma configuração do banco de dados."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_message(username, session_id, role, content, image_data=None):
    """Salva uma mensagem no banco de dados."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (username, session_id, role, content, image_data) VALUES (?, ?, ?, ?, ?)', 
                   (username, session_id, role, content, image_data))
    conn.commit()
    conn.close()

def load_history(username, session_id):
    """Carrega as mensagens de uma sessão específica."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT role, content, image_data FROM history WHERE username = ? AND session_id = ? ORDER BY timestamp ASC', (username, session_id))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1], "image_bytes": row[2]} for row in rows]

def get_all_sessions(username):
    """Recupera a lista de todas as sessões únicas (primeira mensagem como título)."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    # Pega o ID da sessão e a primeira mensagem de cada uma para servir de título
    cursor.execute('''
        SELECT session_id, content FROM history 
        WHERE username = ? AND id IN (SELECT MIN(id) FROM history GROUP BY session_id)
        ORDER BY timestamp DESC
    ''', (username,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def delete_session(session_id):
    """Exclui uma sessão específica do banco de dados."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM history WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

def clear_db():
    """Limpa todo o histórico do banco de dados."""
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM history')
    conn.commit()
    conn.close()

init_db()

# --- SISTEMA DE AUTENTICAÇÃO ---

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password, full_name, email, phone):
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password, full_name, email, phone) VALUES (?, ?, ?, ?, ?)', 
                       (username, hash_password(password), full_name, email, phone))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return True
    return False

def check_user_exists(username):
    """Verifica se um nome de usuário já está cadastrado no banco."""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def delete_user(username):
    """Remove um usuário do banco de dados permanentemente."""
    # 1. Remove do banco de usuários
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()

    # 2. Remove todo o histórico vinculado no banco de histórico
    conn_h = sqlite3.connect(HISTORY_DB)
    cursor_h = conn_h.cursor()
    cursor_h.execute('DELETE FROM history WHERE username = ?', (username,))
    conn_h.commit()
    conn_h.close()

def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

def validate_phone(phone):
    # Validação genérica internacional: + seguido de 10 a 15 dígitos
    return bool(re.match(r'^\+\d{10,15}$', phone))

def validate_password(password):
    if len(password) < 8: return False
    if not any(c.isupper() for c in password): return False
    if not any(c.islower() for c in password): return False
    if not any(c.isdigit() for c in password): return False
    return True

def send_email_verification(email, code):
    """Envia um e-mail real via SMTP (Exemplo usando Gmail)."""
    # --- CONFIGURAÇÃO DE E-MAIL ---
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    SENDER_EMAIL = "l.ocaldasqueiroz@gmail.com" # <--- INSIRA SEU E-MAIL REAL AQUI
    # Certifique-se de usar a Senha de App de 16 dígitos sem espaços
    SENDER_PASSWORD = "vwks vjfs vokk yofx" 

    # Validação simples para evitar erro de placeholder
    if "seu_email" in SENDER_EMAIL or "senha" in SENDER_PASSWORD:
        st.error("Erro: Você precisa configurar seu e-mail e senha de app no arquivo assistente.py")
        return False

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = "Código de Verificação L4M"
    
    corpo = f"Olá! Seu código de verificação para cadastro no L4M é: {code}"
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            # .strip() remove espaços acidentais ao copiar e colar
            server.login(SENDER_EMAIL.strip(), SENDER_PASSWORD.replace(" ", "").strip())
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Falha no Gmail (Verifique a Senha de App): {e}")
        return False

def send_sms_verification(phone, code):
    """Envia um SMS real usando a API do Twilio."""
    # CONFIGURAÇÃO TWILIO (Requer: pip install twilio)
    TWILIO_SID = "ACae75987602830ad677d6e22ac6cfc9b3"
    TWILIO_TOKEN = "689cec0dec4bf0a12f8f5b4f83ea1c1e"
    TWILIO_PHONE = "+19726324262"


    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        
        message = client.messages.create(
            body=f"L4M: Seu codigo de verificacao e {code}",
            from_=TWILIO_PHONE,
            to=phone
        )
        return True
    except Exception as e:
        st.error(f"Falha no Twilio (Verifique SID/Token/Créditos): {e}")
        return False

def generate_code():
    """Gera um código numérico de 6 dígitos."""
    return ''.join(random.choices(string.digits, k=6))

if "awaiting_verification" not in st.session_state:
    st.session_state.awaiting_verification = False

if "authenticated" not in st.session_state:
    # Tenta carregar o usuário persistente do banco de dados
    usuario_salvo = load_setting("logged_user")
    if usuario_salvo:
        st.session_state.authenticated = True
        st.session_state.username = usuario_salvo
    else:
        st.session_state.authenticated = False

if st.session_state.awaiting_verification:
    st.subheader("🛡️ Verificação de Conta")
    st.info(f"Enviamos códigos reais de segurança para {st.session_state.temp_user['email']} e {st.session_state.temp_user['phone']}. Por favor, insira-os abaixo.")
    v_email = st.text_input("Código recebido por E-mail", placeholder="6 dígitos")
    v_sms = st.text_input("Código recebido por SMS", placeholder="6 dígitos")
    
    # Opções de Reenvio de Códigos
    col_re_email, col_re_sms = st.columns(2)
    with col_re_email:
        if st.button("📧 Reenviar E-mail", use_container_width=True):
            st.session_state.email_code = generate_code()
            if send_email_verification(st.session_state.temp_user['email'], st.session_state.email_code):
                st.toast("✅ Novo código enviado ao seu e-mail!")
            else:
                st.error("Não foi possível reenviar o e-mail.")
    with col_re_sms:
        if st.button("📱 Reenviar SMS", use_container_width=True):
            st.session_state.sms_code = generate_code()
            if send_sms_verification(st.session_state.temp_user['phone'], st.session_state.sms_code):
                st.toast("✅ Novo código enviado por SMS!")
            else:
                st.error("Não foi possível reenviar o SMS.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Validar e Cadastrar"):
            if v_email == st.session_state.email_code and v_sms == st.session_state.sms_code:
                u = st.session_state.temp_user
                if create_user(u["username"], u["password"], u["full_name"], u["email"], u["phone"]):
                    st.success("Conta verificada e cadastrada com sucesso! Faça seu login.")
                    st.session_state.awaiting_verification = False
                    del st.session_state.temp_user
                    st.rerun()
                else:
                    st.error("Erro interno ao salvar usuário no banco de dados.")
            else:
                st.error("Um ou mais códigos estão incorretos.")
    with col2:
        if st.button("Cancelar Registro"):
            st.session_state.awaiting_verification = False
            del st.session_state.temp_user
            st.rerun()
    st.stop()

if not st.session_state.authenticated:
    st.info("Por favor, faça login para acessar o assistente L4M.")
    tab_l, tab_r = st.tabs(["🔐 Login", "📝 Cadastro"])
    with tab_l:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")
        manter = st.checkbox("Manter logado", value=True)
        if st.button("Entrar"):
            if authenticate_user(u, p):
                st.session_state.authenticated = True
                st.session_state.username = u
                if manter:
                    save_setting("logged_user", u)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    with tab_r:
        n_full = st.text_input("Nome Completo", key="reg_full")
        n_email = st.text_input("E-mail", key="reg_email")
        
        # Seletor de país e DDI
        col_pais, col_cel = st.columns([0.4, 0.6])
        with col_pais:
            ddi_opcoes = {
                "Brasil (+55)": "+55",
                "Portugal (+351)": "+351",
                "EUA (+1)": "+1",
                "Angola (+244)": "+244",
                "Moçambique (+258)": "+258",
                "Outro (+)": "+"
            }
            pais_selecionado = st.selectbox("País", options=list(ddi_opcoes.keys()), key="reg_country")
            ddi = ddi_opcoes[pais_selecionado]
            
        with col_cel:
            n_phone_raw = st.text_input("Celular (com DDD)", key="reg_phone", help="Apenas números")
        
        nu = st.text_input("Usuário (Login)", key="reg_user")
        if nu and check_user_exists(nu):
            st.error("⚠️ Este nome de usuário já está sendo utilizado. Escolha outro.")

        np = st.text_input("Senha", type="password", key="reg_pass", help="Mínimo 8 caracteres, 1 maiúscula, 1 minúscula e 1 número")
        npc = st.text_input("Confirmar Senha", type="password", key="reg_pass_conf")
        
        if st.button("Criar Conta"):
            # Limpa e formata o telefone final (DDI + números digitados)
            telefone_limpo = f"{ddi}{re.sub(r'\D', '', n_phone_raw)}"
            
            if all([n_full, n_email, n_phone_raw, nu, np, npc]) and not check_user_exists(nu):
                if np != npc:
                    st.error("As senhas não coincidem. Por favor, verifique.")
                elif not validate_email(n_email):
                    st.error("O formato do e-mail digitado é inválido.")
                elif not validate_phone(telefone_limpo):
                    st.error("O formato do celular é inválido para o país selecionado.")
                elif not validate_password(np):
                    st.error("Sua senha deve ter pelo menos 8 caracteres, incluindo uma letra maiúscula, uma minúscula e um número.")
                else:
                    # Inicia o processo de verificação salvando dados temporários
                    st.session_state.temp_user = {
                        "username": nu, "password": np, "full_name": n_full, 
                        "email": n_email, "phone": telefone_limpo
                    }
                    st.session_state.email_code = generate_code()
                    st.session_state.sms_code = generate_code()
                    
                    if send_email_verification(n_email, st.session_state.email_code) and \
                       send_sms_verification(telefone_limpo, st.session_state.sms_code):
                        st.session_state.awaiting_verification = True
                        st.rerun()
                    else:
                        st.error("Erro ao processar o envio dos códigos de segurança.")
            elif nu and check_user_exists(nu):
                st.error("Erro: O nome de usuário escolhido não está disponível.")
            else:
                st.warning("Por favor, preencha todos os campos do formulário.")
    st.stop()

# --- VERIFICAÇÃO DE ATIVAÇÃO POR VOZ (WAKE WORD) ---
if st.query_params.get("mic") == "true":
    st.session_state.auto_start_mic = True
    st.session_state.voice_active = True
    st.session_state.modo_continuo = True
    # Limpa o parâmetro da URL para não reativar o mic se você der F5 na página
    st.query_params.clear()

# --- FRONT-END COM STREAMLIT ---

# Inicializar o histórico de mensagens
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = load_history(st.session_state.username, st.session_state.current_session_id)

if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "pedido_atual" not in st.session_state:
    st.session_state.pedido_atual = None

# Carregar configurações salvas do ElevenLabs
if "eleven_api_key" not in st.session_state:
    st.session_state.eleven_api_key = load_setting("eleven_api_key") or ""
if "eleven_voice_id" not in st.session_state:
    st.session_state.eleven_voice_id = load_setting("eleven_voice_id") or ""

# Barra lateral para opções adicionais
with st.sidebar:
    if os.path.exists(FOTO_PERFIL):
        st.image(FOTO_PERFIL, width='stretch')

    st.subheader("Configurações de Voz")
    st.session_state.voice_active = st.toggle("Ativar Resposta por Voz", value=st.session_state.get("voice_active", False))
    
    # Novo modo para conversação contínua
    st.session_state.modo_continuo = st.toggle("🙌 Modo Mãos Livres", value=st.session_state.get("modo_continuo", False), help="O microfone abre sozinho após a IA responder")

    with st.expander("🎭 Vozes de Personagens (IA)"):
        st.info("Configure sua voz de personagem (Bob Esponja, Ben 10, etc).")
        api_temp = st.text_input("ElevenLabs API Key", value=st.session_state.eleven_api_key, type="password")
        id_temp = st.text_input("Voice ID do Personagem", value=st.session_state.eleven_voice_id)
        if st.button("Salvar e Ativar Voz", width='stretch'):
            st.session_state.eleven_api_key = api_temp
            st.session_state.eleven_voice_id = id_temp
            save_setting("eleven_api_key", api_temp) # Salva no DB
            save_setting("eleven_voice_id", id_temp) # Salva no DB
            st.session_state.selected_voice_name = "🎭 Voz de Personagem (ElevenLabs)"
            st.session_state.voice_active = True
            st.success("Voz de personagem configurada!")
            st.rerun()
        st.markdown("[Encontrar Vozes de Personagens](https://elevenlabs.io/app/voice-library)")
    
    # --- MENU DE SELEÇÃO DE VOZES DO SISTEMA ---
    st.divider()
    st.write("Vozes do Windows (Padrão)")
    try:
        engine_voices = pyttsx3.init()
        available_voices = engine_voices.getProperty('voices')
        voice_names = [v.name for v in available_voices]
        
        # Adiciona a opção da ElevenLabs se as credenciais estiverem salvas
        if st.session_state.get("eleven_api_key") and st.session_state.get("eleven_voice_id"):
            voice_names.insert(0, "🎭 Voz de Personagem (ElevenLabs)")

        # Tenta definir um padrão (PT-BR) se for a primeira execução
        default_idx = 0
        if "selected_voice_name" not in st.session_state:
            for i, v in enumerate(available_voices):
                if "brazil" in v.name.lower() or "portuguese" in v.name.lower():
                    shift = 1 if "🎭 Voz de Personagem (ElevenLabs)" in voice_names else 0
                    default_idx = i + shift
                    break
        else:
            if st.session_state.selected_voice_name in voice_names:
                default_idx = voice_names.index(st.session_state.selected_voice_name)

        selected_voice = st.selectbox("Escolha a Voz do L4M", options=voice_names, index=default_idx)
        st.session_state.selected_voice_name = selected_voice
        
        if selected_voice != "🎭 Voz de Personagem (ElevenLabs)":
            st.session_state.selected_voice_id = next(v.id for v in available_voices if v.name == selected_voice)

    except:
        st.warning("Não foi possível carregar as vozes do sistema.")

    st.divider()
    st.subheader("🎙️ Microfone Manual")
    if st.session_state.get("manual_recorder") is None:
        if st.button("🎤 Iniciar Gravação", width='stretch', help="Clique para começar a falar sem limite de tempo"):
            try:
                st.session_state.manual_recorder = GravadorManual()
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível acessar o microfone: {e}")
    else:
        st.warning("🔴 GRAVANDO... Fale agora.")
        if st.button("⏹️ Parar e Enviar", width='stretch', help="Clique para encerrar a fala e processar o comando"):
            audio_bytes = st.session_state.manual_recorder.parar()
            st.session_state.manual_recorder = None
            r = sr.Recognizer()
            audio_data = sr.AudioData(audio_bytes, 16000, 2)
            try:
                st.toast("⏳ Processando áudio...")
                texto = r.recognize_google(audio_data, language="pt-BR")
                st.session_state.trigger_ai = texto
            except:
                st.error("Não entendi o áudio ou houve um erro no reconhecimento.")
            st.rerun()

    if st.button("🎤 Iniciar Comando de Voz", width='stretch'):
        texto_ouvido = ouvir_microfone()
        if texto_ouvido:
            st.session_state.trigger_ai = texto_ouvido
            st.rerun()

    st.subheader("Acesso Rápido")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💬", key="sidebar_discord", help="Abrir Discord"):
            abrir_aplicativo_windows.func("discord")
    with c2:
        if st.button("🎮", key="sidebar_steam", help="Abrir Steam"):
            abrir_aplicativo_windows.func("steam")
    with c3:
        if st.button("💻", key="sidebar_vscode", help="Abrir VS Code"):
            abrir_aplicativo_windows.func("vscode")

    st.divider()
    st.subheader("Status do Sistema") # Não possui use_container_width, então não precisa de alteração
    # Coleta de métricas de CPU e RAM
    cpu_uso = psutil.cpu_percent()
    memoria = psutil.virtual_memory()
    ram_uso_porcentagem = memoria.percent
    ram_usada_gb = memoria.used / (1024**3)
    ram_total_gb = memoria.total / (1024**3)
    
    st.write(f"**CPU:** {cpu_uso}%")
    st.progress(cpu_uso / 100)
    st.write(f"**RAM:** {ram_usada_gb:.2f} GB / {ram_total_gb:.2f} GB ({ram_uso_porcentagem}%)")
    st.progress(ram_uso_porcentagem / 100)

    st.header("Conversas")
    if st.button("+ Novo Chat", width='stretch'):
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Listar sessões anteriores
    sessions = get_all_sessions(st.session_state.username)
    for sess_id, first_msg in sessions:
        col1, col2 = st.columns([0.82, 0.18])
        titulo = (first_msg[:25] + '...') if len(first_msg) > 25 else first_msg
        with col1:
            if st.button(titulo, key=sess_id, width='stretch'):
                st.session_state.current_session_id = sess_id
                st.session_state.messages = load_history(st.session_state.username, sess_id)
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{sess_id}", width='stretch', help="Excluir esta conversa"):
                delete_session(sess_id)
                # Se a sessão excluída for a que está aberta no momento, limpamos a tela
                if st.session_state.current_session_id == sess_id:
                    st.session_state.current_session_id = str(uuid.uuid4())
                    st.session_state.messages = []
                st.rerun()

    st.divider()
    if st.button("🚪 Sair (Logout)", width='stretch'):
        save_setting("logged_user", None) # Remove a persistência
        st.session_state.authenticated = False
        st.rerun()

    if st.button("🗑️ Deletar Conta", width='stretch', help="Exclui seu cadastro permanentemente"):
        delete_user(st.session_state.username)
        save_setting("logged_user", None)
        st.session_state.authenticated = False
        st.warning("Sua conta foi excluída com sucesso.")
        time.sleep(1.5)
        st.rerun()

    st.divider()
    if st.button("Limpar Tudo"):
        clear_db()
        if "last_audio_base64" in st.session_state:
            del st.session_state.last_audio_base64
        st.rerun()

    st.divider()
    if st.button("🔴 Desligar L4M", help="Encerra o processo da IA completamente"):
        st.error("Encerrando o servidor L4M... Até logo!")
        # Injeta JavaScript para tentar fechar a aba ou limpar a página antes do servidor cair
        st.components.v1.html(
            """
            <script>
                window.stop();
                window.top.location.href = 'about:blank';
            </script>
            """,
            height=0
        )
        time.sleep(1.0) # Aumentamos para 1 segundo para garantir que o navegador navegue para fora
        
        try:
            current_process = psutil.Process(os.getpid())
            # Find the ultimate parent Python process (which should be ligar_L4M.py)
            # Iterate through parents until a non-Python parent or no parent is found
            root_python_process = None
            for p in current_process.parents():
                if "python" in p.name().lower():
                    root_python_process = p
                else:
                    break # Stop if a non-python parent is found

            if root_python_process:
                st.error(f"Tentando encerrar processo raiz com PID: {root_python_process.pid}")
                # Use taskkill /F /T to forcefully terminate the process tree
                result = subprocess.run(f"taskkill /F /T /PID {root_python_process.pid}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    st.success(f"Comando taskkill executado com sucesso para PID {root_python_process.pid}.")
                else:
                    st.error(f"Falha ao executar taskkill para PID {root_python_process.pid}. Erro: {result.stderr}")
            else:
                st.warning("Não foi possível identificar o processo Python pai para encerrar a árvore.")

            os._exit(0) # Force exit the current Streamlit process
        except:
            os._exit(0)

# Exibir mensagens do histórico
for i, message in enumerate(st.session_state.messages):
    # Define o nome que aparece no chat
    nome_exibicao = "L4M" if message["role"] == "assistant" else "user"
    # Usa a foto se for o assistente, senão usa o padrão do usuário
    avatar = FOTO_PERFIL if message["role"] == "assistant" and FOTO_PERFIL else None
    with st.chat_message(nome_exibicao, avatar=avatar):
        if message["role"] == "user":
            col_txt, col_edit = st.columns([0.96, 0.04])
            col_txt.markdown(message["content"])
            if col_edit.button("✏️", key=f"edit_{i}", help="Editar comando e parar IA"):
                st.session_state.is_thinking = False
                st.session_state.pedido_atual = None
                st.toast(f"Editando: {message['content'][:20]}...")
                # O Streamlit não permite preencher o chat_input, mas interromper o fluxo já permite digitar o novo
        else:
            st.markdown(message["content"])
            
        # Se a mensagem tiver uma imagem associada no histórico, exibe ela
        if message.get("image_bytes"):
            try:
                st.image(message["image_bytes"], caption="Imagem do L4M", width='stretch')
                # Botão para baixar a imagem gerada
                st.download_button(
                    label="📥 Baixar Imagem",
                    data=message["image_bytes"],
                    file_name=f"L4M_gerada_{i}.png",
                    mime="image/png",
                    key=f"btn_dl_{i}"
                )
            except Exception as e:
                st.error(f"Erro ao carregar imagem: {e}")

# --- RENDERIZAR ÁUDIO (Se houver) ---
if "last_audio_base64" in st.session_state and st.session_state.last_audio_base64:
    mime = st.session_state.get("last_audio_mime", "audio/mpeg")
    audio_html = f"""
        <audio id="l4m_audio" autoplay>
            <source src="data:{mime};base64,{st.session_state.last_audio_base64}" type="{mime}">
        </audio>
        <script>
            var audio = document.getElementById("l4m_audio");
            audio.volume = 1.0;
            audio.play().catch(function(e) {{ console.log("Autoplay bloqueado:", e); }});
        </script>
    """
    # Aumentamos o tamanho do componente para 2x2 para o browser não "ignorar" o iframe
    st.components.v1.html(audio_html, height=2, width=2)
    st.session_state.last_audio_base64 = None # Limpa para não repetir no próximo rerun

# --- LÓGICA DE AUTO-ATIVAÇÃO DO MICROFONE ---
if st.session_state.pop("auto_start_mic", False):
    # Se a resposta por voz estiver ligada, precisamos esperar o navegador 
    # terminar de falar para o mic não "ouvir a si mesmo"
    if st.session_state.get("voice_active") and st.session_state.messages:
        ultima_msg = st.session_state.messages[-1]
        if ultima_msg["role"] == "assistant":
            # Estima o tempo de fala (média de 12 caracteres por segundo)
            # Adicionamos uma folga de 2 segundos para o carregamento do áudio no browser
            tempo_de_fala = len(ultima_msg["content"]) / 12
            time.sleep(min(tempo_de_fala, 10) + 2.0)
            st.rerun() # Garante que a UI esteja limpa antes de abrir o mic

    texto_ouvido = ouvir_microfone()
    if texto_ouvido:
        st.session_state.trigger_ai = texto_ouvido
        st.rerun()

# Campo de entrada do chat
# --- MENU DE AÇÕES (+) PERTO DO CHAT ---
with st.popover("➕", help="Enviar arquivo"):
    st.subheader("📁 Enviar Arquivo")
    arquivo_enviado = st.file_uploader(f"Upload para {diretorio_atual}", label_visibility="collapsed", key="uploader_bar")
    if arquivo_enviado:
        caminho_final = os.path.join(diretorio_atual, arquivo_enviado.name)
        with open(caminho_final, "wb") as f:
            f.write(arquivo_enviado.getbuffer())
        
        if "ultimo_upload" not in st.session_state or st.session_state.ultimo_upload != arquivo_enviado.name:
            msg_confirmacao = f"Enviei o arquivo: {arquivo_enviado.name}"
            st.session_state.messages.append({"role": "user", "content": msg_confirmacao})
            save_message(st.session_state.username, st.session_state.current_session_id, "user", msg_confirmacao)
            st.session_state.ultimo_upload = arquivo_enviado.name
            st.rerun()
    

prompt_chat = st.chat_input("O que você deseja que eu faça no seu PC?")
prompt = prompt_chat or st.session_state.pop("trigger_ai", None)

# Lógica para iniciar ou manter o "pensamento" da IA
if prompt or st.session_state.is_thinking:
    if prompt:
        st.session_state.pedido_atual = prompt
        st.session_state.is_thinking = True
        if prompt_chat:
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_message(st.session_state.username, st.session_state.current_session_id, "user", prompt)
        st.rerun()

    # --- INTERFACE DE PENSAMENTO ---
    # CSS para esconder a seta de envio e posicionar o botão de interrupção no mesmo local
    st.markdown("""
        <style>
        button[data-testid="stChatInputSubmitButton"] {
            display: none !important;
        }
        [data-testid="stMain"] div[data-testid="stButton"] > button {
            position: fixed;
            bottom: 28px;
            right: 50px;
            z-index: 10000;
            width: 40px !important;
            height: 40px !important;
            border-radius: 50% !important;
            background-color: #ff4b4b !important;
            color: white !important;
            border: none !important;
            padding: 0px !important;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # Botão de Interrupção (🛑) que aparece no lugar da seta
    if st.button("🛑", key="stop_ai", help="Interromper pensamento"):
        st.session_state.is_thinking = False
        st.session_state.pedido_atual = None
        st.toast("Interrompendo...")
        st.rerun()

    avatar_bot = FOTO_PERFIL if os.path.exists(FOTO_PERFIL) else None
    with st.chat_message("L4M", avatar=avatar_bot):
        with st.spinner("Executando tarefa..."):
            try:
                comando = st.session_state.pedido_atual
                # Formatar o histórico recente para dar contexto à IA
                historico_recente = "\n".join([f"{'Usuário' if m['role'] == 'user' else 'L4M'}: {m['content']}" for m in st.session_state.messages[-5:]])
                
                # Executar passando o input dinamicamente
                resultado = equipe.kickoff(inputs={'pedido': comando, 'historico': historico_recente})
                
                st.session_state.is_thinking = False
                resposta = str(resultado)
                st.markdown(resposta)
                falar_texto(resposta)

                st.session_state.messages.append({"role": "assistant", "content": resposta})
                save_message(st.session_state.username, st.session_state.current_session_id, "assistant", resposta)
                
                # Se o modo contínuo estiver ativo, prepara para ouvir novamente após o rerun
                if st.session_state.get("modo_continuo"):
                    st.session_state.auto_start_mic = True
                    
                st.rerun() # Força a atualização para mostrar o título na barra lateral
            except Exception as e:
                st.session_state.is_thinking = False
                erro_msg = f"Erro ao processar: {str(e)}. Verifique se o Ollama está ativo e se o modelo 'llama3.1' foi baixado (`ollama pull llama3.1`)."
                st.error(erro_msg)
                st.session_state.messages.append({"role": "assistant", "content": erro_msg})
                save_message(st.session_state.username, st.session_state.current_session_id, "assistant", erro_msg)
                st.rerun()
