from PIL import Image
import os
import glob

# Caminhos
diretorio = os.path.dirname(os.path.abspath(__file__))
# Procura por qualquer imagem chamada 'avatar' com extensões comuns
padrao = os.path.join(diretorio, "avatar.*")
arquivos_encontrados = glob.glob(padrao)

extensoes_validas = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
entrada = next((f for f in arquivos_encontrados if os.path.splitext(f)[1].lower() in extensoes_validas), None)
saida = os.path.join(diretorio, "avatar.ico")

if entrada:
    img = Image.open(entrada)
    # Garante que a imagem está em modo RGBA para suportar transparência
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    # Salva como ícone com tamanhos padrão do Windows
    img.save(saida, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
    print(f"Sucesso! Ícone criado a partir de '{os.path.basename(entrada)}' em: {saida}")
else:
    print(f"Erro: Nenhuma imagem 'avatar' (.png, .jpg, etc) foi encontrada em {diretorio}")
    print("Arquivos atuais na pasta para conferência:")
    for f in os.listdir(diretorio): print(f" - {f}")