import re
import requests
from bs4 import BeautifulSoup

def baixar_constituicao_completa():
    url = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("🌐 Acessando o Portal do Planalto...")
    try:
        resposta = requests.get(url, headers=headers, timeout=25)
        resposta.encoding = 'utf-8'
        html_puro = resposta.text
    except Exception as e:
        return f"Erro ao acessar o site: {e}"

    print("💉 [VACINA ANTI-BUG] Higienizando código HTML corrompido via Regex...")
    
    # 1. Remove APENAS os textos rasurados que têm abertura e fecho corretos (Lazy Match .*?)
    # Isto limpa 99% do lixo revogado sem correr o risco de apagar o resto da lei
    html_limpo = re.sub(r'<(strike|del|s|strike\s[^>]*|del\s[^>]*|s\s[^>]*?)>.*?</\1>', '', html_puro, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Pulveriza qualquer tag de rasura órfã (aberta ou fechada que o governo esqueceu e que quebrava o parser perto do Art. 24)
    html_limpo = re.sub(r'</?(strike|del|s)\b[^>]*>', '', html_limpo, flags=re.IGNORECASE)

    print("🧠 Parseando HTML higienizado de forma segura...")
    # Com as tags fantasmas removidas, o parser padrão funciona perfeitamente na nuvem!
    soup = BeautifulSoup(html_limpo, 'html.parser')

    # 3. PURGA DE ELEMENTOS INÚTEIS (Scripts, estilos e metadados)
    for lixo in soup.find_all(['script', 'style', 'head', 'title', 'meta']):
        lixo.decompose()

    # 4. EXTRAÇÃO DO TEXTO LIMPO
    texto_bruto = soup.get_text(separator="\n")

    # 5. INJEÇÃO DO PREÂMBULO HISTÓRICO
    preambulo_texto = (
        "PREÂMBULO\n"
        "Nós, representantes do povo brasileiro, reunidos em Assembléia Nacional Constituinte "
        "para instituir um Estado Democrático, destinado a assegurar o exercício dos direitos "
        "sociais e individuais, a liberdade, a segurança, o bem-estar, o desenvolvimento, "
        "a igualdade e a justiça como valores supremos de uma sociedade fraterna, pluralista "
        "e sem preconceitos, fundada na harmonia social e comprometida, na ordem interna "
        "e internacional, com a solução pacífica das controvérsias, promulgamos, sob a "
        "proteção de Deus, a seguinte CONSTITUIÇÃO DA REPÚBLICA FEDERATIVA DO BRASIL.\n"
    )

    print("🧹 Faxina de texto e normalização jurídica...")
    linhas_limpas = []
    passou_do_topo = False
    
    for linha in texto_bruto.split('\n'):
        linha = linha.strip()
        if not linha:
            continue
            
        # Pula assinaturas intermédias e metadados repetitivos do site
        if "Texto compilado" in linha or "Este texto não substitui" in linha:
            continue
            
        # Normaliza indicadores ordinais para evitar quebras no compilador LaTeX
        linha = re.sub(r'\b([0-9]+)[°ºoO]\b', r'\1º', linha)
        linha = re.sub(r'\b([0-9]+)[ªaA]\b', r'\1ª', linha)
        
        # Identifica o início real da matéria constitucional
        if "TÍTULO I" in linha or "Art. 1º" in linha or "Art. 1o" in linha:
            passou_do_topo = True
            
        if passou_do_topo:
            linhas_limpas.append(linha)

    conteudo_final = "\n".join(linhas_limpas)
    
    # Junta o Preâmbulo ao corpo da Constituição
    return preambulo_texto + "\n" + conteudo_final