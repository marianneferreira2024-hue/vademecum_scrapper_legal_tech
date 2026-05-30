import re
import os
import unicodedata
import subprocess
import requests
from bs4 import BeautifulSoup

def raspar_portal_planalto(url):
    try:
        url_limpa = str(url).strip().replace('"', '').replace("'", "").replace('`', '')
        url_limpa = url_limpa.replace('\n', '').replace('\r', '').replace('\t', '')
        url_limpa = "".join(url_limpa.split())
        
        if not url_limpa.lower().startswith("http"):
            return "Erro: A URL fornecida não é válida."

        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        resposta = requests.get(url_limpa, headers=headers, timeout=20)
        resposta.encoding = 'utf-8' if resposta.encoding not in ['ISO-8859-1', 'iso-8859-1'] else 'iso-8859-1'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # 1. TRADUTOR DE QUEBRAS: Converte <br> em quebras de linha reais para não colar rubricas e artigos
        for br in soup.find_all('br'):
            br.replace_with('\n')
            
        paragrafos = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
        
        linhas_texto = []
        for p in paragrafos:
            texto = p.get_text(separator=' ', strip=True)
            # Remove espaços duplos mas preserva os \n que injetámos
            texto = re.sub(r'[ \t\r\f\v]+', ' ', texto) 
            
            for linha in texto.split('\n'):
                linha = linha.strip()
                if linha and len(linha) > 2:
                    linhas_texto.append(linha)
                    
        if not linhas_texto:
            return "Erro: O scraper não conseguiu extrair blocos de texto."
            
        return "\n".join(linhas_texto)
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

def higienizar_unicodes(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKC', texto)
    substituicoes = {
        '\x1c': 'fi', '\x1d': 'fl', '\xa0': ' ', '\u200b': '', '\u200c': '', 
        '\u200d': '', '\ufeff': '', '\x0c': '\n', '–': '-', '—': '-', 
        '“': '"', '”': '"', '‘': "'", '’': "'", '\u0301': ''
    }
    for erro, correcao in substituicoes.items():
        texto = texto.replace(erro, correcao)
    texto = re.sub(r'[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]', '', texto)
    
    # 2. BISTURI DE DESCOLAGEM: Força quebra de linha antes de estruturas escondidas no meio do texto
    texto = re.sub(r'(?<=\S)\s+(Art\.\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(§\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Parágrafo único)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Pena\s*[-–])', r'\n\1', texto)
    
    # 3. ESPAÇAMENTO PÓS-NÚMERO: Corrige "Art. 147-APerseguir" -> "Art. 147-A Perseguir"
    texto = re.sub(r'(Art\.\s*\d+[-A-Za-z0-9ºª]*[\.\-]?)([A-Z])', r'\1 \2', texto)
    texto = re.sub(r'(§\s*\d+[\sºoª\.]*)([A-Z])', r'\1 \2', texto)
    
    return texto

def limpar_texto_latex(texto):
    if not texto: return ""
    texto = texto.replace('§', r'\S{}~').replace('Ÿ', r'\S{}~')
    texto = texto.replace('_', r'\_').replace('&', r'\&').replace('$', r'\$').replace('%', r'\%').replace('#', r'\#')
    texto = texto.replace('nº', r'n.\textsuperscript{o}').replace('Nº', r'N.\textsuperscript{o}').replace('n°', r'n.\textsuperscript{o}')
    texto = texto.replace('[TEXTO REVOGADO]', r'\textbf{\color{gray}[TEXTO REVOGADO]}')
    texto = re.sub(r'(\((?:Redação dada|Incluído|Vide|Revogado|Acrescentado).*?\))', r'\\textit{\1}', texto)
    return texto

def formatar_codigo_penal_para_latex(lista_leis, anos_destaque=None):
    if anos_destaque is None:
        anos_destaque = ['2024', '2025', '2026']
    anos_alvo = [str(a) for a in anos_destaque]
    regex_anos = '|'.join(anos_alvo)
    
    artigos_brutos_totais = []
    ordem_hierarquia = ['NOME_LEI', 'LIVRO', 'TÍTULO', 'CAPÍTULO', 'SEÇÃO', 'SUBSEÇÃO']

    # FASE 1 e 2: TOKENIZAÇÃO INTELIGENTE
    for nome_lei, texto_bruto in lista_leis:
        texto_completo = f"# NOME_LEI {nome_lei}\n" + texto_bruto
        texto_limpo = higienizar_unicodes(texto_completo)
        
        hierarquia_ativa = {k: None for k in ordem_hierarquia}
        linhas_validas = []
        
        def resetar_niveis_abaixo(nivel):
            idx = ordem_hierarquia.index(nivel)
            for k in ordem_hierarquia[idx+1:]:
                hierarquia_ativa[k] = None

        for l in texto_limpo.split('\n'):
            l = l.strip()
            if not l or "googleusercontent.com" in l or "immersive_entry_chip" in l: continue
            
            if l.startswith('# NOME_LEI '):
                hierarquia_ativa['NOME_LEI'] = l.replace('# NOME_LEI ', '').strip()
                resetar_niveis_abaixo('NOME_LEI')
                continue
                
            match_est = re.match(r'^(LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\s+', l, re.IGNORECASE)
            if match_est:
                tipo_est = match_est.group(1).upper()
                tipo_est = tipo_est.replace('TITULO', 'TÍTULO').replace('CAPITULO', 'CAPÍTULO').replace('SECAO', 'SEÇÃO').replace('SUBSECAO', 'SUBSEÇÃO')
                hierarquia_ativa[tipo_est] = l
                resetar_niveis_abaixo(tipo_est)
                continue
                
            token = None
            match_art = re.match(r'^(Art\.\s*\d+[-A-Za-z0-9ºª]*)\s*[\.\-–—]?\s*(.*)', l)
            if match_art:
                token = {'tipo': 'ARTIGO', 'nome': match_art.group(1).strip(), 'resto': match_art.group(2).strip(), 'hierarquia': dict(hierarquia_ativa)}
            else:
                match_par = re.match(r'^(§\s*\d+[\sºoª\.]*|Parágrafo\s+único)\s*[\.\-–—]?\s*(.*)', l, re.IGNORECASE)
                if match_par:
                    token = {'tipo': 'PARAGRAFO', 'nome': match_par.group(1).strip(), 'resto': match_par.group(2).strip()}
                else:
                    match_inc = re.match(r'^([IVXLC]+)\s*[\.\-–—]\s*(.*)', l)
                    if match_inc and match_inc.group(1) != "VETADO":
                        token = {'tipo': 'INCISO', 'nome': match_inc.group(1).strip(), 'resto': match_inc.group(2).strip()}
                    else:
                        match_ali = re.match(r'^([a-z])\)\s*(.*)', l)
                        if match_ali:
                            token = {'tipo': 'ALINEA', 'nome': match_ali.group(1).strip(), 'resto': match_ali.group(2).strip()}
                        else:
                            # COLA SEMÂNTICA RESTRITA: Só cola se for letra minúscula ou notas entre parênteses
                            is_pena = l.lower().startswith('pena')
                            is_nota_rodape = l.startswith('(') and ('Lei' in l or 'Redação' in l or 'Incluído' in l or 'Vide' in l)
                            is_continuacao = l[0].islower() or l.startswith(',') or l.startswith(';')
                            
                            if linhas_validas and not is_pena and (is_continuacao or is_nota_rodape):
                                ultimo_tipo = linhas_validas[-1]['tipo']
                                if ultimo_tipo in ['ARTIGO', 'PARAGRAFO', 'INCISO', 'ALINEA']:
                                    linhas_validas[-1]['resto'] = (linhas_validas[-1]['resto'] + " " + l).strip()
                                    continue
                                elif ultimo_tipo == 'TEXTO':
                                    linhas_validas[-1]['texto'] = (linhas_validas[-1]['texto'] + " " + l).strip()
                                    continue