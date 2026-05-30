import re
import os
import unicodedata
import subprocess
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

def raspar_portal_planalto(url):
    try:
        url_limpa = str(url).strip().replace('"', '').replace("'", "").replace('`', '')
        url_limpa = url_limpa.replace('\n', '').replace('\r', '').replace('\t', '')
        url_limpa = "".join(url_limpa.split())
        
        if not url_limpa.lower().startswith("http"):
            return "Erro: A URL fornecida não é válida."

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        }
        
        resposta = session.get(url_limpa, headers=headers, timeout=30)
        resposta.encoding = 'utf-8' if resposta.encoding not in ['ISO-8859-1', 'iso-8859-1'] else 'iso-8859-1'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        for br in soup.find_all('br'):
            br.replace_with('\n')
            
        paragrafos = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
        linhas_texto = []
        for p in paragrafos:
            texto = p.get_text(separator=' ', strip=True)
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
    
    texto = re.sub(r'(?<=\S)\s+(Art\.\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(§\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Parágrafo único)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Pena\s*[-–])', r'\n\1', texto)
    
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
                            
                            token = {'tipo': 'TEXTO', 'texto': l}

            if token:
                linhas_validas.append(token)

        bloco_artigo_atual = None
        for token in linhas_validas:
            if token['tipo'] == 'ARTIGO':
                if bloco_artigo_atual:
                    artigos_brutos_totais.append(bloco_artigo_atual)
                bloco_artigo_atual = {'tipo': 'BLOCO_ARTIGO', 'artigo': token, 'conteudo': [], 'hierarquia': token['hierarquia']}
            else:
                if bloco_artigo_atual:
                    bloco_artigo_atual['conteudo'].append(token)
        if bloco_artigo_atual:
            artigos_brutos_totais.append(bloco_artigo_atual)

    artigos_filtrados = []
    for b in artigos_brutos_totais:
        texto_caput = b['artigo'].get('nome', '') + " " + b['artigo'].get('resto', '')
        caput_tem_ano = any(ano in texto_caput for ano in anos_alvo)
        
        regex_novo = rf'\((Incluído|Acrescentado|Inserido).*?({regex_anos})\)'
        caput_novo_integral = caput_tem_ano and re.search(regex_novo, texto_caput, re.IGNORECASE)
        
        if caput_novo_integral:
            sub_itens_alterados = b['conteudo']
        else:
            itens_para_manter = set()
            idx_paragrafo_atual = -1
            idx_inciso_atual = -1
            
            for i, c in enumerate(b['conteudo']):
                tipo = c['tipo']
                if tipo == 'PARAGRAFO': 
                    idx_paragrafo_atual = i
                    idx_inciso_atual = -1 
                elif tipo == 'INCISO': 
                    idx_inciso_atual = i

                texto_c = c.get('nome', '') + " " + c.get('resto', '') + " " + c.get('texto', '')
                is_pena = (tipo == 'TEXTO' and texto_c.strip().lower().startswith('pena'))
                
                if any(ano in texto_c for ano in anos_alvo) or (caput_tem_ano and is_pena):
                    itens_para_manter.add(i)
                    if tipo == 'ALINEA' and idx_inciso_atual != -1:
                        itens_para_manter.add(idx_inciso_atual)
                        if idx_paragrafo_atual != -1:
                            itens_para_manter.add(idx_paragrafo_atual)
                    elif tipo == 'INCISO' and idx_paragrafo_atual != -1:
                        itens_para_manter.add(idx_paragrafo_atual)

            sub_itens_alterados = [c for i, c in enumerate(b['conteudo']) if i in itens_para_manter]
        
        if not caput_tem_ano and len(sub_itens_alterados) == 0:
            continue
            
        b['conteudo'] = sub_itens_alterados
        artigos_filtrados.append(b)


    documento_latex = []
    documento_latex.append(r"\documentclass[10pt,a4paper,twocolumn]{article}") 
    documento_latex.append(r"\usepackage[utf8x]{inputenc}")
    documento_latex.append(r"\usepackage[T1]{fontenc}")
    documento_latex.append(r"\usepackage[brazilian]{babel}")
    documento_latex.append(r"\usepackage{lmodern}") 
    documento_latex.append(r"\usepackage[top=1.6cm,bottom=1.8cm,left=1.2cm,right=1.2cm]{geometry}")
    documento_latex.append(r"\usepackage{enumitem}")
    documento_latex.append(r"\usepackage[most]{tcolorbox}")
    documento_latex.append(r"\usepackage{xcolor}")
    documento_latex.append(r"\usepackage[hidelinks]{hyperref}") 
    documento_latex.append(r"\usepackage[protrusion=true,expansion=false]{microtype}") 
    
    documento_latex.append(r"\setlist{noitemsep, topsep=2pt, parsep=0pt, partopsep=0pt}")
    documento_latex.append(r"\newtcolorbox{artigoBox}[1]{enhanced, width=\linewidth, breakable, colback=gray!4, colframe=gray!60, coltitle=black, fonttitle=\bfseries\normalsize, title=#1, attach title to upper=\par\vspace{2pt}, arc=1mm, boxrule=0.5pt, left=2mm, right=2mm, top=1.5mm, bottom=1.5mm, before=\par\vspace{0.1cm}, after=\par}")
    documento_latex.append(r"\definecolor{corAtualizacao}{rgb}{0.0, 0.35, 0.65}") 
    documento_latex.append(r"\newcommand{\marcadorNovo}{\textbf{\color{corAtualizacao}}[Lei Recente]~}")
    
    documento_latex.append(r"\begin{document}")
    
    documento_latex.append(r"\twocolumn[{")
    documento_latex.append(r"  \begin{center}{\LARGE \textbf{Compilação Exclusiva de Alterações Legislativas}}\par\vspace{0.2cm}")
    documento_latex.append(r"  {\large Atualizações: " + ", ".join(anos_alvo) + r"}\par\vspace{0.6cm}\end{center}")
    documento_latex.append(r"}]")
    
    documento_latex.append(r"\renewcommand{\contentsname}{Índice de Leis e Artigos Alterados}")
    documento_latex.append(r"\tableofcontents\vspace{0.6cm}\hrule\vspace{0.4cm}")
    
    em_lista_inciso = False; em_lista_alinea = False
    def fechar_listas():
        nonlocal em_lista_alinea, em_lista_inciso
        if em_lista_alinea: documento_latex.append("        \\end{enumerate}"); em_lista_alinea = False
        if em_lista_inciso: documento_latex.append("    \\end{enumerate}"); em_lista_inciso = False

    last_printed = {k: None for k in ordem_hierarquia}

    for b in artigos_filtrados:
        h = b['hierarquia']
        
        if h['NOME_LEI'] != last_printed['NOME_LEI']:
            fechar_listas()
            texto_lei = limpar_texto_latex(h['NOME_LEI'])
            documento_latex.append(r"\clearpage")
            documento_latex.append(r"\twocolumn[{")
            documento_latex.append(f"  \\begin{{center}}\\vspace{{0.5cm}}\\noindent\\textbf{{\\LARGE {texto_lei}}}\\par\\vspace{{0.2cm}}\\hrule\\vspace{{0.4cm}}\\end{{center}}")
            documento_latex.append(r"}]")
            documento_latex.append(r"\phantomsection")
            nome_limpo = texto_lei.replace(r'\textsuperscript{o}', 'o')
            documento_latex.append(f"\\addcontentsline{{toc}}{{section}}{{{nome_limpo}}}")
            last_printed['NOME_LEI'] = h['NOME_LEI']
            
            for k in ordem_hierarquia[1:]:
                last_printed[k] = None
                
        for nivel in ['LIVRO', 'TÍTULO', 'CAPÍTULO', 'SEÇÃO', 'SUBSEÇÃO']:
            if h[nivel] != last_printed[nivel]:
                if h[nivel]: 
                    texto_est = limpar_texto_latex(h[nivel])
                    documento_latex.append(r"\phantomsection")
                    if nivel in ['LIVRO', 'TÍTULO']:
                        documento_latex.append(f"\\addcontentsline{{toc}}{{subsection}}{{{texto_est}}}")
                    else:
                        documento_latex.append(f"\\addcontentsline{{toc}}{{subsubsection}}{{{texto_est}}}")
                    documento_latex.append(f"\\vspace{{0.3cm}}\\noindent\\textbf{{\\large {texto_est}}}\\par\\vspace{{0.1cm}}")
                
                last_printed[nivel] = h[nivel]
                idx = ordem_hierarquia.index(nivel)
                for k in ordem_hierarquia[idx+1:]:
                    last_printed[k] = None

        art = b['artigo']
        nome_art = limpar_texto_latex(art.get('nome', ''))
        resto_art = limpar_texto_latex(art.get('resto', ''))
        
        documento_latex.append(r"\phantomsection")
        documento_latex.append(f"\\begin{{artigoBox}}{{{nome_art}}}")
        
        if resto_art:
            pref = r"\marcadorNovo " if any(a in resto_art for a in anos_alvo) else ""
            documento_latex.append(f"\\noindent {pref}{resto_art}\\par\\vspace{{2pt}}")
            
        for c in b['conteudo']:
            texto_item_bruto = c.get('resto','') + c.get('texto','')
            pref_c = r"\marcadorNovo " if any(a in texto_item_bruto for a in anos_alvo) else ""
            
            if c['tipo'] == 'PARAGRAFO':
                fechar_listas()
                nome_p = limpar_texto_latex(c.get('nome', ''))
                resto_p = limpar_texto_latex(c.get('resto', ''))
                documento_latex.append(f"\n\\noindent \\textbf{{{nome_p}}} {pref_c}{resto_p}\\par\\vspace{{2pt}}")
            elif c['tipo'] == 'INCISO':
                if em_lista_alinea: documento_latex.append("        \\end{enumerate}"); em_lista_alinea = False
                if not em_lista_inciso:
                    documento_latex.append("    \\begin{enumerate}[label=\\textbf{\\Roman* -}, leftmargin=0.7cm]")
                    em_lista_inciso = True
                documento_latex.append(f"        \\item {pref_c}{limpar_texto_latex(c.get('resto', ''))}")
            elif c['tipo'] == 'ALINEA':
                if not em_lista_inciso:
                    documento_latex.append("    \\begin{enumerate}[label=\\textbf{\\Roman* -}, leftmargin=0.7cm]"); em_lista_inciso = True
                if not em_lista_alinea:
                    documento_latex.append("        \\begin{enumerate}[label=\\textbf{\\alph*)}, leftmargin=0.5cm]"); em_lista_alinea = True
                documento_latex.append(f"            \\item {pref_c}{limpar_texto_latex(c.get('resto', ''))}")
            elif c['tipo'] == 'TEXTO':
                fechar_listas()
                txt = limpar_texto_latex(c.get('texto', ''))
                if txt.startswith("Pena"): txt = re.sub(r'^Pena\s*[-–\.]?\s*(.*)', r'\\textbf{Pena -} \1', txt)
                documento_latex.append(f"\n\\noindent {pref_c}{txt}\\par\\vspace{{2pt}}")
                
        fechar_listas()
        documento_latex.append("\\end{artigoBox}")
            
    documento_latex.append(r"\end{document}")
    
    codigo_latex = "\n".join(documento_latex)
    return codigo_latex

def compilar_pdf(lista_leis, nome_base="VadeMecum_Minerado", anos_destaque=None):
    if os.name != 'nt':
        diretorio_base = "/tmp"
    else:
        diretorio_base = os.path.dirname(os.path.abspath(__file__))
        
    arquivo_tex = os.path.join(diretorio_base, f"{nome_base}.tex")
    arquivo_pdf = os.path.join(diretorio_base, f"{nome_base}.pdf")
    
    codigo_tex = formatar_codigo_penal_para_latex(lista_leis, anos_destaque)
    
    with open(arquivo_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    comando = [
        "pdflatex", "-interaction=nonstopmode", "-halt-on-error",
        f"-output-directory={diretorio_base}", arquivo_tex
    ]
    if os.name == 'nt': comando.insert(3, "-screendialogs=no")
        
    try:
        subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        compilacao = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        if os.path.exists(arquivo_pdf):
            return "sucesso", arquivo_pdf
            
        arquivo_log = os.path.join(diretorio_base, f"{nome_base}.log")
        detalhe_erro = ""
        if os.path.exists(arquivo_log):
            with open(arquivo_log, "r", encoding="utf-8", errors="ignore") as l:
                detalhe_erro = "\n".join(l.readlines()[-30:])
        return "erro", f"Log LaTeX:\n{detalhe_erro}\n\nTerminal:\n{compilacao.stdout}"
    except Exception as e:
        return "erro", f"Falha de execução: {str(e)}"