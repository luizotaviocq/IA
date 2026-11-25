import os
import subprocess
import time
import base64
import webbrowser
import unicodedata
import glob
import urllib.parse
import shlex
import datetime
import math
import requests
from PIL import Image
import pyautogui
from crewai.tools import tool
from duckduckgo_search import DDGS

@tool("focar_janela_windows")
def focar_janela_windows(nome_app: str):
    """
    Traz um aplicativo já aberto para o primeiro plano (foco). 
    Use isto OBRIGATORIAMENTE antes de 'digitar_texto_no_pc' para garantir que o texto vá para o app correto.
    Exemplo de nomes: 'Discord', 'Chrome', 'Notepad', 'Spotify'.
    """
    try:
        # Pequena espera para o sistema estar pronto
        time.sleep(0.5)
        # Escapa o título para segurança no PowerShell
        titulo_escapado = nome_app.replace("'", "''")
        cmd_focus = ["powershell", "-Command", f"(New-Object -ComObject WScript.Shell).AppActivate('{titulo_escapado}')"]
        subprocess.run(cmd_focus, capture_output=True)
        return f"Sucesso: Tentativa de focar na janela '{nome_app}' executada."
    except Exception as e:
        return f"Erro ao focar janela: {str(e)}"

# 2. Criar a função que permite abrir aplicativos no Windows
@tool("abrir_aplicativo_windows")
def abrir_aplicativo_windows(nome_do_app: str):
    """
    Abre qualquer coisa no Windows: aplicativos (chrome, notepad), 
    pastas (C:\\, documentos), arquivos (foto.jpg, doc.pdf) ou sites (google.com).
    """
    try:
        if not nome_do_app:
            return "Erro: Nenhum nome de aplicativo ou recurso foi fornecido."
            
        # Remove acentos e caracteres especiais para melhor compatibilidade (ex: discórdia -> discord)
        nome_normalizado = "".join(
            c for c in unicodedata.normalize('NFD', nome_do_app)
            if unicodedata.category(c) != 'Mn'
        )
        app_nome_minusculo = nome_normalizado.lower().strip()

        # Função auxiliar interna para tentar trazer a janela para frente
        def focar_janela(termo_titulo, espera=1):
            time.sleep(espera) # Aguarda o processo carregar a interface
            # Escapa o título para segurança no PowerShell
            titulo_escapado = termo_titulo.replace("'", "''")
            cmd_focus = ["powershell", "-Command", f"(New-Object -ComObject WScript.Shell).AppActivate('{titulo_escapado}')"]
            subprocess.run(cmd_focus, capture_output=True)

        # --- MAPEAMENTO DE APPS COMPLEXOS E JOGOS ---
        local_app_data = os.getenv('LOCALAPPDATA', '')

        # Valorant (Exige protocolo da Riot)
        if "valorant" in app_nome_minusculo:
            os.startfile("riotclient://launch-app=valorant --launch-patchline=live")
            focar_janela("VALORANT")
            return "Sucesso: Valorant iniciado via Riot Protocol."

        # GTA V / Grand Theft Auto (Steam AppID 271590)
        if "gta" in app_nome_minusculo or "grand theft auto" in app_nome_minusculo:
            os.startfile("steam://run/271590")
            focar_janela("Grand Theft Auto V", espera=10) # GTA demora a carregar
            return "Sucesso: Comando enviado para abrir GTA V na Steam."

        # FiveM (Geralmente no LocalAppData)
        if "fivem" in app_nome_minusculo:
            fivem_path = os.path.join(local_app_data, "FiveM", "FiveM.exe")
            if os.path.exists(fivem_path):
                os.startfile(fivem_path)
                focar_janela("FiveM")
                return "Sucesso: FiveM iniciado do caminho local."
            os.startfile("fivem://") # Tenta protocolo se o arquivo não estiver no local padrão
            focar_janela("FiveM")
            return "Comando FiveM enviado via protocolo."

        # Medal (Localizado no LocalAppData)
        if "medal" in app_nome_minusculo:
            medal_exe = os.path.join(local_app_data, "Medal", "Medal.exe")
            if os.path.exists(medal_exe):
                os.startfile(medal_exe)
                focar_janela("Medal")
                return "Sucesso: Medal iniciado."

        # Nvidia (NVIDIA App, Painel de Controle e GeForce Experience)
        if "nvidia" in app_nome_minusculo or "nvidea" in app_nome_minusculo:
            nvidia_app_exe = r"C:\Program Files\NVIDIA Corporation\NVIDIA App\CEF\NVIDIA App.exe"
            if os.path.exists(nvidia_app_exe):
                os.startfile(nvidia_app_exe)
                focar_janela("NVIDIA")
                return "Sucesso: NVIDIA App iniciado."

            # Fallbacks para versões de drivers mais antigas
            subprocess.Popen("start nvcplui.exe", shell=True) 
            focar_janela("NVIDIA Control Panel")
            subprocess.Popen("start nvgeforceexperience.exe", shell=True)
            return "Sucesso: NVIDIA App não encontrado. Abrindo Painel de Controle e GeForce Experience."

        # Lógica para URLs: Verifica prefixos ou extensões de domínio, garantindo que não seja um caminho de arquivo
        is_url = app_nome_minusculo.startswith(("http://", "https://", "www.")) or \
                 (any(ext in app_nome_minusculo for ext in [".com", ".br", ".net", ".org"]) and not os.path.sep in nome_do_app)

        if is_url and not os.path.exists(nome_do_app):
            url = nome_do_app if nome_do_app.startswith("http") else f"https://{nome_do_app}"
            webbrowser.open(url)
            return f"Sucesso: O site '{url}' foi aberto no navegador padrão."

        # Lógica específica para Launchers (Steam e Epic)
        if "rocket league" in app_nome_minusculo:
            # Protocolo específico para Rocket League na Epic Games
            os.startfile("com.epicgames.launcher://apps/Sugar?action=launch&silent=true")
            return "Comando enviado para iniciar o Rocket League via Epic Games Launcher."

        if "steam" in app_nome_minusculo:
            os.startfile("steam://open/main")
            return "Comando enviado para abrir a interface da Steam."
            
        if "epic" in app_nome_minusculo:
            os.startfile("com.epicgames.launcher://")
            return "Comando enviado para abrir a Epic Games Launcher."
            
        if "riot" in app_nome_minusculo:
            os.startfile("riotclient://")
            return "Comando enviado para abrir o Riot Client (League of Legends / Valorant)."

        # Lógica específica para o VS Code
        if "vscode" in app_nome_minusculo or "vs code" in app_nome_minusculo:
            subprocess.Popen("code", shell=True)
            return "Sucesso: O Visual Studio Code foi iniciado."

        # Lógica específica para o Discord (ele fica escondido no LocalAppData)
        if "discord" in app_nome_minusculo:
            # Caminho padrão no Windows: AppData/Local/Discord
            discord_dir = os.path.join(local_app_data, 'Discord')
            discord_launcher = os.path.join(discord_dir, 'Update.exe')
            
            if os.path.exists(discord_launcher):
                try:
                    # Tentativa 1: Via launcher oficial com diretório de trabalho correto
                    subprocess.Popen(f'start "" "{discord_launcher}" --processStart Discord.exe', shell=True, cwd=discord_dir)
                    focar_janela("Discord")
                    return "Sucesso: O comando para iniciar o Discord foi enviado. Aguarde ele carregar totalmente antes de enviar mensagens."
                except:
                    pass

            # Tentativa 2: Via protocolo de sistema (muitas vezes registrado no Windows)
            try:
                os.startfile("discord://")
                focar_janela("Discord")
                return "Sucesso: Discord iniciado via protocolo. Trazendo para o primeiro plano."
            except:
                pass

            # 3. Busca dinâmica por versões (ex: app-1.0.x)
            search_pattern = os.path.join(discord_dir, 'app-*', 'Discord.exe')
            found_paths = glob.glob(search_pattern)
            if found_paths:
                # Pega a versão mais recente encontrada
                latest_version = sorted(found_paths)[-1]
                os.startfile(latest_version)
                focar_janela("Discord")
                return f"Discord encontrado em versão específica: {latest_version}. Iniciando e focando..."

        # Tenta abrir usando o método padrão do Windows (como se desse dois cliques)
        try:
            try:
                # Tentativa 1: os.startfile (Caminhos e arquivos) - Caminho absoluto é mais seguro
                abs_path = os.path.abspath(nome_do_app)
                os.startfile(abs_path if os.path.exists(abs_path) else nome_do_app)
                return f"Sucesso: O recurso '{nome_do_app}' foi aberto."
            except:
                # Tentativa 2: Shell Start seguro usando lista para evitar injeção
                subprocess.Popen(["cmd", "/c", "start", "", nome_do_app], shell=False)
                return f"Sucesso: Comando de abertura enviado para '{nome_do_app}'."
        except Exception as e:
            return f"Erro ao tentar enviar o comando de abertura para '{app_nome_minusculo}': {str(e)}"
            
    except Exception as e:
        return f"Erro ao abrir o aplicativo '{nome_do_app}': {str(e)}"

@tool("fechar_aplicativo_windows")
def fechar_aplicativo_windows(nome_do_app: str):
    """
    Fecha um aplicativo ou processo em execução no Windows pelo nome (ex: chrome, discord, powershell, notepad).
    """
    try:
        # Limpa o nome para o formato de processo (.exe)
        processo = nome_do_app.lower().strip().replace(".exe", "")
        
        # SEGURANÇA: Evita que a IA feche a si mesma ou o terminal onde o script roda
        if processo in ["powershell", "cmd", "python", "streamlit"]:
            return f"Aviso: Não posso fechar o '{processo}' por segurança, pois eu dependo dele para funcionar!"

        # O comando taskkill usando lista de argumentos para maior segurança
        cmd = ["taskkill", "/F", "/IM", f"{processo}.exe", "/T"]
        resultado = subprocess.run(cmd, capture_output=True, text=True)
        
        if resultado.returncode == 0:
            return f"Sucesso: O processo '{processo}' foi encerrado."
        else:
            return f"Aviso: Não foi possível fechar '{processo}'. Talvez ele não esteja aberto."
    except Exception as e:
        return f"Erro ao tentar fechar o aplicativo: {str(e)}"

@tool("buscar_arquivo_computador")
def buscar_arquivo_computador(termo: str):
    """
    Procura por arquivos ou pastas que contenham o termo no nome dentro das pastas do usuário 
    (Documentos, Downloads, Desktop e Menu Iniciar). Útil para encontrar programas instalados.
    """
    try:
        user_path = os.path.expanduser("~")
        program_data = os.environ.get("ProgramData", "C:\\ProgramData")
        
        # Definimos as pastas principais para a busca ser rápida
        pastas_alvo = [
            os.path.join(user_path, "Desktop"),
            os.path.join(user_path, "Documents"),
            os.path.join(user_path, "Downloads"),
            # Pastas onde ficam os atalhos de programas instalados no Windows
            os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(user_path, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
        ]
        
        resultados = []
        for pasta in pastas_alvo:
            if not os.path.exists(pasta): continue
            for root, dirs, files in os.walk(pasta):
                # Limita a profundidade para 3 níveis para encontrar pastas de programas
                if root.count(os.sep) - pasta.count(os.sep) > 3: continue
                
                for item in files + dirs:
                    if termo.lower() in item.lower():
                        resultados.append(os.path.join(root, item))
                        if len(resultados) >= 3: break # Retorna os 3 primeiros
                if len(resultados) >= 3: break
        
        if resultados:
            return "Encontrei estes caminhos:\n" + "\n".join(resultados) + "\nEscolha um para abrir."
        return f"Não encontrei nenhum arquivo chamado '{termo}' nas pastas comuns."
    except Exception as e:
        return f"Erro durante a busca: {str(e)}"

@tool("abrir_google_no_navegador")
def abrir_google_no_navegador(consulta: str):
    """
    Abre o navegador Google Chrome/Edge com uma pesquisa pronta. 
    Use APENAS se o usuário quiser VER visualmente os resultados no navegador. Se ele apenas fizer uma pergunta, use 'pesquisar_google'.
    """
    try:
        query_codificada = urllib.parse.quote(consulta)
        url = f"https://www.google.com/search?q={query_codificada}"
        webbrowser.open(url)
        return f"Sucesso: Página de busca por '{consulta}' aberta no navegador."
    except Exception as e:
        return f"Erro ao abrir navegador: {str(e)}"

@tool("pesquisar_google")
def pesquisar_google(consulta: str):
    """
    PESQUISA OBRIGATÓRIA: Use sempre que o usuário fizer uma pergunta sobre fatos, preços (dólar, moedas), clima, notícias ou dúvidas gerais. 
    Retorna informações em tempo real da internet.
    """
    try:
        with DDGS() as ddgs:
            # Removemos o timelimit fixo para permitir encontrar páginas de produtos e sites que não mudam todo dia
            search_results = list(ddgs.text(consulta, region='br-pt', max_results=10))
            
            if search_results:
                return "\n".join([f"- Fonte: {r['href']} | Título: {r['title']} | Resumo: {r['body']}" for r in search_results])
            return f"Não encontrei informações recentes sobre '{consulta}' na internet."
    except Exception as e:
        return f"Erro ao acessar a internet: {str(e)}. Verifique sua conexão ou tente novamente."

@tool("ler_conteudo_arquivo")
def ler_conteudo_arquivo(caminho: str):
    """
    Lê o conteúdo de um arquivo de texto (.txt, .md, .py, .log) ou PDF no computador.
    Use esta ferramenta quando o usuário pedir para 'ler', 'resumir' ou 'analisar' o conteúdo de um documento.
    """
    try:
        caminho_limpo = caminho.strip().strip('"').strip("'")
        if not os.path.exists(caminho_limpo):
            return f"Erro: O arquivo '{caminho_limpo}' não foi encontrado."

        ext = os.path.splitext(caminho_limpo)[1].lower()
        if ext in [".txt", ".md", ".py", ".log", ".json", ".csv", ".docx"]:
            if ext == ".docx":
                try:
                    import docx
                    doc = docx.Document(caminho_limpo)
                    return f"Conteúdo do Word:\n\n" + "\n".join([p.text for p in doc.paragraphs])[:5000]
                except ImportError:
                    return "Erro: Para ler .docx, instale a biblioteca: pip install python-docx"
            
            with open(caminho_limpo, "r", encoding="utf-8", errors="ignore") as f:
                return f"Conteúdo do arquivo:\n\n{f.read(5000)}"
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(caminho_limpo)
                # Extrai texto das primeiras 10 páginas, ignorando páginas vazias ou que são apenas imagens
                paginas = [page.extract_text() for page in reader.pages[:10]]
                texto = "\n".join([p for p in paginas if p])
                return f"Conteúdo do PDF:\n\n{texto[:5000]}"
            except ImportError:
                return "Erro: Para ler arquivos PDF, instale a biblioteca necessária rodando: pip install pypdf"
            except Exception as e:
                return f"Erro ao processar o PDF: {str(e)}"
        return f"Erro: Extensão {ext} não suportada."
    except Exception as e:
        return f"Erro ao ler arquivo: {str(e)}"

@tool("analisar_imagem")
def analisar_imagem(caminho: str):
    """
    Analisa ou descreve o conteúdo de uma imagem (PNG, JPG, JPEG). 
    Use quando o usuário pedir para 'ver', 'identificar' ou 'descrever' uma foto.
    """
    try:
        caminho_limpo = caminho.strip().strip('"').strip("'")
        if not os.path.exists(caminho_limpo):
            return "Erro: Imagem não encontrada."
        with open(caminho_limpo, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        payload = {"model": "llava", "prompt": "Descreva esta imagem em detalhes em português.", "stream": False, "images": [base64_image]}
        response = requests.post("http://localhost:11434/api/generate", json=payload)
        if response.status_code == 200:
            return f"Análise: {response.json().get('response')}"
        return "Erro ao analisar a imagem."
    except Exception as e:
        return f"Erro na análise visual: {str(e)}"

@tool("digitar_texto_no_pc")
def digitar_texto_no_pc(texto: str, tecla_final: str = "enter"):
    """
    Digita um texto no teclado simulando um usuário real. 
    Use para enviar mensagens, preencher formulários ou pesquisar dentro de aplicativos.
    Certifique-se de que o aplicativo alvo está em primeiro plano (focado) antes de usar.
    """
    try:
        # Pequena pausa para o Windows processar o foco da janela
        time.sleep(0.5)
        # Escreve o texto. O intervalo evita erros em campos de input rápidos
        pyautogui.write(texto, interval=0.01)
        if tecla_final:
            pyautogui.press(tecla_final)
        return f"Sucesso: O texto foi digitado e a tecla '{tecla_final}' foi pressionada."
    except Exception as e:
        return f"Erro ao digitar texto: {str(e)}"

@tool("pressionar_teclas_atalho")
def pressionar_teclas_atalho(teclas: str):
    """
    Pressiona uma combinação de teclas de atalho (ex: 'ctrl, c', 'win, r', 'ctrl, k').
    As teclas devem ser separadas por vírgula. Útil para abrir menus internos de apps.
    """
    try:
        lista_teclas = [t.strip().lower() for t in teclas.split(',')]
        pyautogui.hotkey(*lista_teclas)
        return f"Sucesso: Atalho '{teclas}' executado."
    except Exception as e:
        return f"Erro ao executar atalho: {str(e)}"

@tool("obter_data_hora")
def obter_data_hora():
    """
    Retorna a data e hora atual do sistema. Use sempre que o usuário perguntar que dia é hoje ou a hora.
    """
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

@tool("executar_calculo_matematico")
def executar_calculo_matematico(expressao: str):
    """
    Executa cálculos matemáticos (soma, subtração, multiplicação, divisão, porcentagens, raízes, potências).
    Use sempre que o usuário pedir para calcular algo ou para realizar conversões de moeda após obter a taxa.
    Exemplo: '4324 * 5.40' ou '(1500 + 300) * 0.10'.
    """
    try:
        # Limpeza básica para aceitar vírgula como ponto decimal (padrão BR)
        expr_limpa = expressao.replace(',', '.')
        # Dicionário de funções matemáticas seguras
        safe_dict = {"abs": abs, "round": round, "sqrt": math.sqrt, "pow": pow, "pi": math.pi, "e": math.e}
        
        resultado = eval(expr_limpa, {"__builtins__": None}, safe_dict)
        return f"Cálculo realizado: {expressao} = {resultado}"
    except Exception as e:
        return f"Erro ao calcular: {str(e)}. Use operadores padrão: +, -, *, /, ** para potência."