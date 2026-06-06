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
        resposta = requests.get(url, headers=headers, timeout=15)
        resposta.encoding = 'utf-8' # Força o encoding correto do Planalto
    except Exception as e:
        return f"Erro ao acessar o site: {e}"

    print("🧠 Parseando HTML com motor avançado (html5lib)...")
    # O html5lib reconstrói tags de <strike> ou <font> que o governo esqueceu de fechar perto do Art. 24
    soup = BeautifulSoup(resposta.text, 'html5lib')

    # 1. PURGA DO LIXO (Limpa scripts, estilos e notas laterais inúteis)
    for lixo in soup.find_all(['script', 'style', 'head', 'title']):
        lixo.decompose()

    # 2. TRATAMENTO SENSÍVEL DE TEXTOS REVOGADOS
    # Se o governo esqueceu de fechar uma tag de risco, não queremos apagar a lei inteira.
    for tag_riscada in soup.find_all(['strike', 'del', 's']):
        if len(tag_riscada.get_text()) < 4000: # Limite seguro para um artigo longo revogado
            tag_riscada.decompose()

    # 3. EXTRAÇÃO DO TEXTO BRUTO
    texto_bruto = soup.get_text(separator="\n")

    # 4. CAPTURA E INJEÇÃO DO PREÂMBULO
    # O site do planalto costuma avacalhar o preâmbulo, vamos isolá-lo ou injetá-lo cirurgicamente
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
    
    # Limpezas de espaçamento excessivo do site do Planalto
    linhas_limpas = []
    passou_do_topo = False
    
    for linha in texto_bruto.split('\n'):
        linha = linha.strip()
        if not linha:
            continue
            
        # Pula as notas de rodapé de digitação do Planalto e menus do site
        if "Texto compilado" in linha or "Este texto não substitui" in linha or "Brasília," in linha:
            continue
            
        # Alinha e limpa os indicadores ordinais que enganam o LaTeX
        linha = re.sub(r'\b([0-9]+)[°ºoO]\b', r'\1º', linha)
        linha = re.sub(r'\b([0-9]+)[ªaA]\b', r'\1ª', linha)
        
        # Identifica onde a matéria real da constituição começa (geralmente TÍTULO I ou Art. 1º)
        if "TÍTULO I" in linha or "Art. 1º" in linha:
            passou_do_topo = True
            
        if passou_do_topo:
            linhas_limpas.append(linha)

    # Une o texto limpo
    conteudo_final = "\n".join(linhas_limpas)
    
    # Junta o Preâmbulo antes do Título I
    texto_com_preambulo = preambulo_texto + "\n" + conteudo_final

    return texto_com_preambulo

# Teste de Mesa isolado
if __name__ == "__main__":
    resultado = baixar_constituicao_completa()
    
    # Validação rápida de salvamento
    with open("constituicao_limpa.txt", "w", encoding="utf-8") as f:
        f.write(resultado)
        
    print("\n📊 --- RELATÓRIO DE EXTRAÇÃO ---")
    print(f"Tamanho do arquivo: {len(resultado)} caracteres.")
    
    # Verificação se foi além do Artigo 24
    if "Art. 25" in resultado or "Art. 201" in resultado:
        print("✅ SUCESSO: O Scraper quebrou a barreira do Artigo 24 e extraiu os artigos subsequentes!")
    else:
        print("❌ ALERTA: O texto ainda parece truncado. Verifique o arquivo 'constituicao_limpa.txt'")