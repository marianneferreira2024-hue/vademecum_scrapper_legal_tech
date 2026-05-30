import re
import os
import unicodedata
import subprocess
import requests
from bs4 import BeautifulSoup

def raspar_portal_planalto(url):
    """Faz o Web Scraping em tempo real do portal do Planalto."""
    try:
        url_limpa = str(url).strip().replace('"', '').replace("'", "").replace('`', '')
        url_limpa = url_limpa.replace('\n', '').replace('\r', '').replace('\t', '')
        url_limpa = "".join(url_limpa.split())
        
        if not url_limpa.lower().startswith("http"):
            return f"Erro: A URL fornecida não é válida."

        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        resposta = requests.get(url_limpa, headers=headers, timeout=20)
        resposta.encoding = 'utf-8' if resposta.encoding not in ['ISO-8859-1', 'iso-8859-1'] else 'iso-8859-1'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        paragrafos = soup.find_all(['p', 'span', 'font'])
        linhas_texto = [re.sub(r'\s+', ' ', p.get_text().strip()) for p in paragrafos if p.get_text().strip()]
                
        if not linhas_texto:
            return "Erro: O scraper não conseguiu extrair blocos de texto."
            
        return "\n".join(linhas_texto)
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

def higienizar_unicodes(texto):
    if not texto: return ""
    substituicoes = {
        '\x1c': 'fi', '\x1d': 'fl', '\xa0': ' ', '\u200b': '', '\u200c': '', 
        '\u200d': '', '\ufeff': '', '\x0c': '\n', '–': '-', '—': '-', 
        '“': '"', '”': '"', '‘': "'", '’': "'"
    }
    for erro, correcao in substituicoes.items():
        texto = texto.replace(erro, correcao)
    return re.sub(r'[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]', '', texto)

def limpar_texto_latex(texto):
    if not texto: return ""
    texto = texto.replace('§', r'\S{}~').replace('Ÿ', r'\S{}~')
    texto = texto.replace('_', r'\_').replace('&', r'\&').replace('$', r'\$').replace('%', r'\%').replace('#', r'\#')
    texto = texto.replace('nº', r'n.\textsuperscript{o}').replace('Nº', r'N.\textsuperscript{o}').replace('n°', r'n.\textsuperscript{o}')
    texto = texto.replace('[TEXTO REVOGADO]', r'\textbf{\color{gray}[TEXTO REVOGADO]}')
    texto = re.sub(r'(\((?:Redação dada|Incluído|Vide|Revogado|Acrescentado).*?\))', r'\\textit{\1}', texto)
    return texto

def verificador_pre_compilacao_latex(codigo_latex):
    codigo_latex = re.sub(r'\\begin\{artigoBox\}\{[^\}]*\}\s*\\end\{artigoBox\}', '', codigo_latex)
    codigo_latex = re.sub(r'\\begin\{multicols\}\{2\}\s*\\end\{multicols\}', '', codigo_latex)
    codigo_latex = re.sub(r'(\\par\\vspace\{\d+pt\}\s*){2,}', r'\\par\\vspace{2pt}\n', codigo_latex)
    codigo_latex = re.sub(r'(\\vspace\{\d+\.\d+cm\}\s*){2,}', r'\\vspace{0.3cm}\n', codigo_latex)
    return codigo_latex

def formatar_codigo_penal_para_latex(lista_leis, anos_destaque=None):
    if anos_destaque is None:
        anos_destaque = ['2024', '2025', '2026']
    anos_alvo = [str(a) for a in anos_destaque]
    regex_anos = '|'.join(anos_alvo)
    
    blocos_brutos_totais = []

    # 🔴 FASE 1 e 2: TOKENIZAÇÃO E AGRUPAMENTO HIERÁRQUICO POR LEI
    for nome_lei, texto_bruto in lista_leis:
        # Injeta o nome da lei como âncora para a lógica de tokens
        texto_completo = f"# {nome_lei}\n" + texto_bruto
        texto_limpo = higienizar_unicodes(texto_completo)
        
        linhas_validas = []
        for l in texto_limpo.split('\n'):
            l = l.strip()
            if not l or "googleusercontent.com" in l or "immersive_entry_chip" in l: continue
            
            if l.startswith('# '):
                linhas_validas.append({'tipo': 'NOME_LEI', 'texto': l.replace('#', '').strip()})
                continue
                
            if re.match(r'^(LIVRO|TÍTULO|CAPÍTULO|SEÇÃO|SUBSEÇÃO)\s+', l):
                linhas_validas.append({'tipo': 'ESTRUTURA', 'texto': l})
                continue
                
            match_art = re.match(r'^(Art\.\s*\d+[-A-Za-z0-9ºª]*)\s*[\.\-–—]?\s*(.*)', l)
            if match_art:
                linhas_validas.append({'tipo': 'ARTIGO', 'nome': match_art.group(1).strip(), 'resto': match_art.group(2).strip()})
                continue
                
            match_par = re.match(r'^(§\s*\d+[\sºoª\.]*|Parágrafo\s+único)\s*[\.\-–—]?\s*(.*)', l, re.IGNORECASE)
            if match_par:
                linhas_validas.append({'tipo': 'PARAGRAFO', 'nome': match_par.group(1).strip(), 'resto': match_par.group(2).strip()})
                continue
                
            match_inc = re.match(r'^([IVXLC]+)\s*[\.\-–—]\s*(.*)', l)
            if match_inc and match_inc.group(1) != "VETADO":
                linhas_validas.append({'tipo': 'INCISO', 'nome': match_inc.group(1).strip(), 'resto': match_inc.group(2).strip()})
                continue
                
            match_ali = re.match(r'^([a-z])\)\s*(.*)', l)
            if match_ali:
                linhas_validas.append({'tipo': 'ALINEA', 'nome': match_ali.group(1).strip(), 'resto': match_ali.group(2).strip()})
                continue
                
            # A SUPER-COLA SEMÂNTICA
            is_pena = l.lower().startswith('pena')
            if linhas_validas and not is_pena:
                ultimo_tipo = linhas_validas[-1]['tipo']
                if ultimo_tipo in ['ARTIGO', 'PARAGRAFO', 'INCISO', 'ALINEA']:
                    linhas_validas[-1]['resto'] = (linhas_validas[-1]['resto'] + " " + l).strip()
                    continue
                elif ultimo_tipo == 'TEXTO':
                    linhas_validas[-1]['texto'] = (linhas_validas[-1]['texto'] + " " + l).strip()
                    continue
            
            linhas_validas.append({'tipo': 'TEXTO', 'texto': l})

        # Agrupamento (Fase 2)
        bloco_artigo_atual = None
        for token in linhas_validas:
            if token['tipo'] in ['ESTRUTURA', 'NOME_LEI']:
                if bloco_artigo_atual:
                    blocos_brutos_totais.append(bloco_artigo_atual)
                    bloco_artigo_atual = None
                blocos_brutos_totais.append(token)
            elif token['tipo'] == 'ARTIGO':
                if bloco_artigo_atual:
                    blocos_brutos_totais.append(bloco_artigo_atual)
                bloco_artigo_atual = {'tipo': 'BLOCO_ARTIGO', 'artigo': token, 'conteudo': []}
            else:
                if bloco_artigo_atual:
                    bloco_artigo_atual['conteudo'].append(token)
        if bloco_artigo_atual:
            blocos_brutos_totais.append(bloco_artigo_atual)

    # 🟢 FASE 3: O BISTURI CIRÚRGICO
    blocos_filtrados = []
    
    for b in blocos_brutos_totais:
        if b['tipo'] in ['ESTRUTURA', 'NOME_LEI']:
            blocos_filtrados.append(b)
            continue
            
        if b['tipo'] == 'BLOCO_ARTIGO':
            texto_caput = b['artigo'].get('nome', '') + " " + b['artigo'].get('resto', '')
            caput_tem_ano = any(ano in texto_caput for ano in anos_alvo)
            
            # Regex dinâmica adaptada aos anos selecionados
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
            blocos_filtrados.append(b)

    # 🟡 FASE 4: O DESTRUIDOR DE TÍTULOS FANTASMAS
    final_elementos = []
    estruturas_pendentes = [] 
    
    for b in blocos_filtrados:
        if b['tipo'] in ['ESTRUTURA', 'NOME_LEI']:
            estruturas_pendentes.append(b) 
        elif b['tipo'] == 'BLOCO_ARTIGO':
            final_elementos.extend(estruturas_pendentes)
            estruturas_pendentes = [] 
            final_elementos.append(b)

    # 🔵 FASE 5: MONTAGEM LATEX
    documento_latex = []
    documento_latex.append(r"\documentclass[10pt,a4paper]{article}") 
    documento_latex.append(r"\usepackage[utf8]{inputenc}")
    documento_latex.append(r"\usepackage[T1]{fontenc}")
    documento_latex.append(r"\usepackage[brazilian]{babel}")
    documento_latex.append(r"\usepackage{lmodern}") # ESSENCIAL PARA O SERVIDOR CLOUD
    documento_latex.append(r"\usepackage[top=1.5cm,bottom=1.5cm,left=1.2cm,right=1.2cm]{geometry}")
    documento_latex.append(r"\usepackage{enumitem}")
    documento_latex.append(r"\usepackage[most]{tcolorbox}")
    documento_latex.append(r"\usepackage{xcolor}")
    documento_latex.append(r"\usepackage[hidelinks]{hyperref}") 
    documento_latex.append(r"\usepackage{multicol}")
    documento_latex.append(r"\usepackage[protrusion=true,expansion=false]{microtype}") # BLINDAGEM CONTRA ESTOURO
    
    documento_latex.append(r"\setlist{noitemsep, topsep=2pt, parsep=0pt, partopsep=0pt}")
    
    # Caixa ajustada com width=\linewidth para evitar margens vazadas
    documento_latex.append(r"\newtcolorbox{artigoBox}[1]{enhanced, width=\linewidth, breakable, colback=gray!4, colframe=gray!60, coltitle=black, fonttitle=\bfseries\normalsize, title=#1, attach title to upper=\par\vspace{2pt}, arc=1mm, boxrule=0.5pt, left=2mm, right=2mm, top=1.5mm, bottom=1.5mm, before=\par\vspace{0.1cm}, after=\par}")
    documento_latex.append(r"\definecolor{corAtualizacao}{rgb}{0.0, 0.35, 0.65}") 
    documento_latex.append(r"\newcommand{\marcadorNovo}{\textbf{\color{corAtualizacao}}[Lei Recente]~}")
    
    documento_latex.append(r"\begin{document}")
    documento_latex.append(r"\begin{center}{\LARGE \textbf{Compilação Exclusiva de Alterações Legislativas}}\\[0.2cm]{\large Atualizações de " + " a ".join(anos_alvo) + r"}\\[0.6cm]\end{center}")
    documento_latex.append(r"\renewcommand{\contentsname}{Índice de Leis e Artigos Alterados}")
    documento_latex.append(r"\tableofcontents\vspace{0.6cm}\hrule\vspace{0.4cm}")
    documento_latex.append(r"\begin{multicols}{2}")
    
    em_lista_inciso = False; em_lista_alinea = False
    
    def fechar_listas():
        nonlocal em_lista_alinea, em_lista_inciso
        if em_lista_alinea: documento_latex.append("        \\end{enumerate}"); em_lista_alinea = False
        if em_lista_inciso: documento_latex.append("    \\end{enumerate}"); em_lista_inciso = False

    for el in final_elementos:
        if el['tipo'] == 'NOME_LEI':
            fechar_listas()
            texto_lei = limpar_texto_latex(el.get('texto', ''))
            documento_latex.append(r"\phantomsection")
            documento_latex.append(f"\\addcontentsline{{toc}}{{section}}{{{texto_lei}}}")
            documento_latex.append(f"\\end{{multicols}}\\vspace{{0.5cm}}\\noindent\\textbf{{\\Large {texto_lei}}}\\par\\vspace{{0.2cm}}\\hrule\\vspace{{0.4cm}}\\begin{{multicols}}{{2}}")
            
        elif el['tipo'] == 'ESTRUTURA':
            texto_est = limpar_texto_latex(el.get('texto', ''))
            documento_latex.append(r"\phantomsection")
            documento_latex.append(f"\\addcontentsline{{toc}}{{subsection}}{{{texto_est}}}")
            documento_latex.append(f"\\vspace{{0.3cm}}\\noindent\\textbf{{\\large {texto_est}}}\\par\\vspace{{0.1cm}}")
            
        elif el['tipo'] == 'BLOCO_ARTIGO':
            art = el['artigo']
            nome_art = limpar_texto_latex(art.get('nome', ''))
            resto_art = limpar_texto_latex(art.get('resto', ''))
            
            documento_latex.append(r"\phantomsection")
            documento_latex.append(f"\\addcontentsline{{toc}}{{subsubsection}}{{{nome_art}}}")
            documento_latex.append(f"\\begin{{artigoBox}}{{{nome_art}}}")
            
            if resto_art:
                pref = r"\marcadorNovo " if any(a in resto_art for a in anos_alvo) else ""
                documento_latex.append(f"\\noindent {pref}{resto_art}\\par\\vspace{{2pt}}")
                
            for c in el['conteudo']:
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
            
    documento_latex.append(r"\end{multicols}\end{document}")
    
    codigo_latex_bruto = "\n".join(documento_latex)
    return verificador_pre_compilacao_latex(codigo_latex_bruto)

def compilar_pdf(lista_leis, nome_base="VadeMecum_Minerado", anos_destaque=None):
    # Rotas seguras que detectam se o sistema é o Windows Local ou a Nuvem (Linux)
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
        # PRIMEIRA PASSAGEM: Criação do Índice (.toc)
        subprocess.run(
            comando, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # SEGUNDA PASSAGEM: Renderização e alinhamento do texto PDF real
        compilacao = subprocess.run(
            comando, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
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