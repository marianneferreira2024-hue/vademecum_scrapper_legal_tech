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
        import requests
        from bs4 import BeautifulSoup
        import re
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        url_limpa = str(url).strip().replace('"', '').replace("'", "").replace('`', '')
        url_limpa = "".join(url_limpa.split())
        
        if not url_limpa.lower().startswith("http"):
            return "Erro: A URL fornecida não é válida."

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        resposta = session.get(url_limpa, headers=headers, timeout=30)
        resposta.encoding = 'utf-8' if resposta.encoding not in ['ISO-8859-1', 'iso-8859-1'] else 'iso-8859-1'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # 1. DESTRUIR LIXO (Remove textos revogados, scripts e estilos)
        for tag in soup.find_all(['strike', 'del', 's', 'script', 'style']):
            tag.decompose()
            
        # 2. PROTEGER BLOCOS (Em vez de separar tudo, isolamos apenas parágrafos e títulos)
        tags_bloco = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr']
        for tag in soup.find_all(tags_bloco):
            tag.insert_before('\n')
            tag.insert_after('\n')
            
        for br in soup.find_all('br'):
            br.replace_with('\n')
            
        # 3. EXTRAÇÃO CIRÚRGICA (Sem separador para não partir tags <b> e <span> a meio)
        if soup.body:
            texto_bruto = soup.body.get_text()
        else:
            texto_bruto = soup.get_text()
            
        # 4. HIGIENIZAÇÃO DE VÍCIOS DO PLANALTO
        # Garante que "Art." comece sempre numa linha nova (às vezes fica colado a um título)
        texto_bruto = re.sub(r'(?<!\n)(Art\.\s*\d+)', r'\n\1', texto_bruto)
        
        # Corrige as letras "o" minúsculas usadas erradamente pelo Governo como símbolo ordinal (ex: Art. 2o vira Art. 2º)
        texto_bruto = re.sub(r'(Art\.\s*\d+)[oO]\b', r'\1º', texto_bruto)
        texto_bruto = re.sub(r'(§\s*\d+)[oO]\b', r'\1º', texto_bruto)
            
        linhas_texto = []
        for linha in texto_bruto.split('\n'):
            linha = linha.strip()
            # Limpa espaços duplos
            linha = re.sub(r'[ \t\r\f\v]+', ' ', linha)
            
            # Guarda apenas linhas úteis e estruturadas
            if linha and len(linha) > 2 and not linha.startswith("Mensagem de"):
                linhas_texto.append(linha)
                    
        if not linhas_texto:
            return "Erro: O scraper não conseguiu extrair blocos de texto ou o documento foi revogado."
            
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
    
    # Padroniza espaçamentos antes de quebras estruturais legítimas
    texto = re.sub(r'(?<=\S)\s+(Art\.\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(§\s*\d)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Parágrafo único)', r'\n\1', texto)
    texto = re.sub(r'(?<=\S)\s+(Pena\s*[-–])', r'\n\1', texto)
    
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
    modo_completo = "VADE COMPLETO" in anos_alvo
    
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
            if not l or "googleusercontent.com" in l or "immersive_entry_chip" in l or l in ["Vigência", "Produção de efeitos"]:
                continue
            
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
            
            # --- ALGORITMO DE AGLUTINAÇÃO INTELIGENTE (FURA QUEBRAS DO PLANALTO) ---
            if linhas_validas:
                ultimo_token = linhas_validas[-1]
                texto_anterior = ultimo_token['resto'] if ultimo_token['tipo'] != 'TEXTO' else ultimo_token['texto']
                
                is_pena = l.lower().startswith('pena')
                is_nota_rodape = bool(re.search(r'^\s*[\(\[]?(Lei|Redação|Incluído|Vide|Revogado|Acrescentado|Decreto|Medida)', l, re.IGNORECASE))
                is_continuacao_direta = l[0].islower() or l.startswith(',') or l.startswith(';') or l.startswith('.') or l.startswith(')')
                
                # Verifica se a linha anterior terminou com um conector óbvio cortado a meio
                terminou_pendente = bool(re.search(r'(Lei|nº|n°|no|do|da|pela|pelo|de|em|\()\s*$', texto_anterior, re.IGNORECASE))
                # Verifica se a linha atual completa uma citação isolada (ex: "15.397, de 2026)")
                completa_citacao = bool(re.search(r'^\s*\d+.*?de\s+\d{4}\)', l))

                if not is_pena and (is_continuacao_direta or is_nota_rodape or terminou_pendente or completa_citacao):
                    if ultimo_token['tipo'] in ['ARTIGO', 'PARAGRAFO', 'INCISO', 'ALINEA']:
                        linhas_validas[-1]['resto'] = (linhas_validas[-1]['resto'] + " " + l).strip()
                    else:
                        linhas_validas[-1]['texto'] = (linhas_validas[-1]['texto'] + " " + l).strip()
                    continue
            # -----------------------------------------------------------------------

            token = None
            match_art = re.match(r'^(Art\.\s*\d+[-A-Za-z0-9ºª]*)\s*[\.\-–—]?\s*(.*)', l)
            if match_art:
                token = {'tipo': 'ARTIGO', 'nome': match_art.group(1).strip(), 'resto': match_art.group(2).strip(), 'hierarquia': dict(hierarquia_ativa)}
            else:
                match_par = re.match(r'^(§\s*\d+[-A-Za-z0-9ºª\s\.]*|Parágrafo\s+único)\s*[\.\-–—]?\s*(.*)', l, re.IGNORECASE)
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
    # 1. ADICIONE ESTA LINHA PARA DETETAR A FLAG DO VADE COMPLETO
    modo_completo = "VADE COMPLETO" in anos_alvo

    for b in artigos_brutos_totais:
        
        # 2. SE FOR MODO COMPLETO, ADICIONA O ARTIGO INTEIRO À LISTA FINAL E SALTA O RESTO DA ANÁLISE!
        if modo_completo:
            artigos_filtrados.append(b)
            continue
            
        texto_caput = b['artigo'].get('nome', '') + " " + b['artigo'].get('resto', '')
        caput_tem_ano = any(ano in texto_caput for ano in anos_alvo)
        
        regex_novo = rf'\((Incluído|Acrescentado|Inserido|Redação dada).*?({regex_anos})\)'
        # ... resto do código existente do bisturi ...
    for b in artigos_brutos_totais:
        texto_caput = b['artigo'].get('nome', '') + " " + b['artigo'].get('resto', '')
        caput_tem_ano = any(ano in texto_caput for ano in anos_alvo)
        
        regex_novo = rf'\((Incluído|Acrescentado|Inserido|Redação dada).*?({regex_anos})\)'
        caput_novo_integral = caput_tem_ano and re.search(regex_novo, texto_caput, re.IGNORECASE)
        
        if caput_novo_integral:
            sub_itens_alterados = b['conteudo']
        else:
            itens_para_manter = set()
            idx_paragrafo_atual = -1
            idx_inciso_atual = -1
            idx_alinea_atual = -1
            ultimo_estrutural = -1
            
            for i, c in enumerate(b['conteudo']):
                tipo = c['tipo']
                if tipo == 'PARAGRAFO': 
                    idx_paragrafo_atual = i
                    idx_inciso_atual = -1 
                    idx_alinea_atual = -1
                    ultimo_estrutural = i
                elif tipo == 'INCISO': 
                    idx_inciso_atual = i
                    idx_alinea_atual = -1
                    ultimo_estrutural = i
                elif tipo == 'ALINEA':
                    idx_alinea_atual = i
                    ultimo_estrutural = i

                texto_c = c.get('nome', '') + " " + c.get('resto', '') + " " + c.get('texto', '')
                is_pena = (tipo == 'TEXTO' and texto_c.strip().lower().startswith('pena'))
                
                if any(ano in texto_c for ano in anos_alvo) or (caput_tem_ano and is_pena):
                    itens_para_manter.add(i)
                    if tipo == 'ALINEA':
                        if idx_inciso_atual != -1: itens_para_manter.add(idx_inciso_atual)
                        if idx_paragrafo_atual != -1: itens_para_manter.add(idx_paragrafo_atual)
                    elif tipo == 'INCISO':
                        if idx_paragrafo_atual != -1: itens_para_manter.add(idx_paragrafo_atual)
                    elif tipo == 'TEXTO':
                        if ultimo_estrutural != -1:
                            itens_para_manter.add(ultimo_estrutural)
                            parent_tipo = b['conteudo'][ultimo_estrutural]['tipo']
                            if parent_tipo == 'ALINEA':
                                if idx_inciso_atual != -1: itens_para_manter.add(idx_inciso_atual)
                                if idx_paragrafo_atual != -1: itens_para_manter.add(idx_paragrafo_atual)
                            elif parent_tipo == 'INCISO':
                                if idx_paragrafo_atual != -1: itens_para_manter.add(idx_paragrafo_atual)

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
    # SÓ CARREGA O MICROTYPE SE NÃO FOR O VADE COMPLETO GIGANTE
    if not modo_completo:
        documento_latex.append(r"\usepackage[protrusion=true,expansion=false]{microtype}") 
        
    documento_latex.append(r"\setlist{noitemsep, topsep=2pt, parsep=0pt, partopsep=0pt}")
    documento_latex.append(r"\newtcolorbox{artigoBox}[1]{enhanced, width=\linewidth, breakable, colback=gray!4, colframe=gray!60, coltitle=black, fonttitle=\bfseries\normalsize, title=#1, attach title to upper=\par\vspace{2pt}, arc=1mm, boxrule=0.5pt, left=2mm, right=2mm, top=1.5mm, bottom=1.5mm, before=\par\vspace{0.1cm}, after=\par}")
    documento_latex.append(r"\definecolor{corAtualizacao}{rgb}{0.0, 0.35, 0.65}") 
    documento_latex.append(r"\newcommand{\marcadorNovo}{\textbf{\color{corAtualizacao}}[Lei Recente]~}")
    documento_latex.append(r"\begin{document}")
    
    documento_latex.append(r"\twocolumn[{")
    # 1. Abrimos o center AQUI
    documento_latex.append(r"  \begin{center}{\LARGE \textbf{Compilação Exclusiva de Alterações Legislativas}}\par\vspace{0.2cm}")
    
    # 2. Mantemos o texto da autora (repare que REMOVI o \end{center} que estava no final desta linha)
    documento_latex.append(r"  {\large Desenvolvido por: Marianne Ramos Ferreira}\par\vspace{0.2cm}")
    
    # 3. Colocamos as atualizações e fechamos o center APENAS UMA VEZ no final
    # (Adicionei também uma proteção com 'str(a)' para evitar que anos em formato numérico quebrem o código)
    documento_latex.append(r"  {\large Atualizações: " + ", ".join([str(a) for a in anos_alvo]) + r"}\par\vspace{0.6cm}\end{center}")
    documento_latex.append(r"}]")
    
    documento_latex.append(r"\renewcommand{\contentsname}{Índice de Leis e Artigos Alterados}")
    documento_latex.append(r"\tableofcontents\vspace{0.6cm}\hrule\vspace{0.4cm}")
    
    em_lista_inciso = False; em_lista_alinea = False
    def fechar_listas():
        nonlocal em_lista_alinea, em_lista_inciso
        if em_lista_alinea: documento_latex.append("        \\end{enumerate}"); em_lista_alinea = False
        if em_lista_inciso: documento_latex.append("    \\end{enumerate}"); em_lista_inciso = False

    last_printed = {k: None for k in ordem_hierarquia}

    # ADICIONE ESTA LINHA (se ainda não tiver) antes do loop dos artigos:
    # ... o seu código anterior que faz o filtro do bisturi ...

    # 1. DETETA SE É O VADE COMPLETO
    modo_completo = "VADE COMPLETO" in anos_alvo

    # 2. DICIONÁRIO DE HIERARQUIA (Para não perdermos os Livros, Títulos e Capítulos)
    niveis_hierarquia = ['PARTE', 'LIVRO', 'TITULO', 'CAPITULO', 'SECAO', 'SUBSECAO']
    last_printed = {k: None for k in niveis_hierarquia}

    # 3. O LOOP PRINCIPAL
    for b in artigos_filtrados:
        
        # --- IMPRIME A HIERARQUIA (Títulos, Capítulos, etc.) ---
        if 'hierarquia' in b:
            for nivel in niveis_hierarquia:
                if nivel in b['hierarquia'] and b['hierarquia'][nivel] != last_printed[nivel]:
                    valor = b['hierarquia'][nivel]
                    if valor:
                        texto_nivel = limpar_texto_latex(valor)
                        documento_latex.append(f"\\vspace{{0.4cm}}\\noindent\\begin{{center}}\\textbf{{{texto_nivel}}}\\end{{center}}\\vspace{{0.2cm}}")
                    last_printed[nivel] = valor

        # --- IMPRIME O ARTIGO ---
        art = b['artigo']
        
        # Salvaguarda: Se o Art. 1º vier sem nome, forçamos a identificação
        nome_art = limpar_texto_latex(art.get('nome', ''))
        resto_art = limpar_texto_latex(art.get('resto', ''))
        
        # Se por acaso o "nome" estiver vazio mas o "resto" tiver texto (erro comum no Art 1º do Planalto)
        if not nome_art and resto_art.lower().startswith("art"):
            nome_art = "Art. 1º " # Força o nome
            
        documento_latex.append(r"\phantomsection")
        
        # LÓGICA DO BYPASS: Caixas para atualizações, Texto Limpo para Vade Completo
        if modo_completo:
            documento_latex.append(f"\\vspace{{0.3cm}}\\noindent\\textbf{{{nome_art}}} ")
        else:
            documento_latex.append(f"\\begin{{artigoBox}}{{{nome_art}}}")
            
        if resto_art:
            pref = r"\marcadorNovo " if any(a in resto_art for a in anos_alvo) and not modo_completo else ""
            documento_latex.append(f"\\noindent {pref}{resto_art}\\par\\vspace{{2pt}}")
            
        # --- IMPRIME PARÁGRAFOS E ALÍNEAS ---
        for c in b['conteudo']:
            texto_item_bruto = c.get('resto','') + c.get('texto','')
            pref_c = r"\marcadorNovo " if any(a in texto_item_bruto for a in anos_alvo) and not modo_completo else ""
            
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
                if not em_lista_alinea:
                    margem = "0.7cm" if not em_lista_inciso else "0.5cm"
                    documento_latex.append(f"        \\begin{{enumerate}}[label=\\textbf{{\\alph*)}}, leftmargin={margem}]"); em_lista_alinea = True
                documento_latex.append(f"            \\item {pref_c}{limpar_texto_latex(c.get('resto', ''))}")
            elif c['tipo'] == 'TEXTO':
                fechar_listas()
                txt = limpar_texto_latex(c.get('texto', ''))
                if txt.startswith("Pena"): txt = re.sub(r'^Pena\s*[-–\.]?\s*(.*)', r'\\textbf{Pena -} \1', txt)
                documento_latex.append(f"\n\\noindent {pref_c}{txt}\\par\\vspace{{2pt}}")
                
        fechar_listas()
        
        # FECHA A CAIXA OU DÁ ESPAÇAMENTO DE TEXTO
        if not modo_completo:
            documento_latex.append("\\end{artigoBox}")
        else:
            documento_latex.append("\\par") 
            
    # FECHA O DOCUMENTO FINAL
    documento_latex.append(r"\end{document}")
    
    return "\n".join(documento_latex)

def compilar_pdf(lista_leis, nome_base="VadeMecum_Minerado", anos_destaque=None):
    if os.name != 'nt':
        diretorio_base = "/tmp"
    else:
        diretorio_base = os.path.dirname(os.path.abspath(__file__))
        
    arquivo_tex = os.path.join(diretorio_base, f"{nome_base}.tex")
    arquivo_pdf = os.path.join(diretorio_base, f"{nome_base}.pdf")
    
    # 1. NOVO: ROTINA DE LIMPEZA DO LIXO ANTERIOR (Previne o Runaway argument)
    extensoes_lixo = ['.aux', '.toc', '.out', '.log']
    for ext in extensoes_lixo:
        arquivo_temp = os.path.join(diretorio_base, f"{nome_base}{ext}")
        if os.path.exists(arquivo_temp):
            try:
                os.remove(arquivo_temp)
            except:
                pass
                
    # 2. Gera o novo código tex
    codigo_tex = formatar_codigo_penal_para_latex(lista_leis, anos_destaque)
    
    with open(arquivo_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    comando = [
        "pdflatex", "-interaction=nonstopmode", "-halt-on-error",
        f"-output-directory={diretorio_base}", arquivo_tex
    ]
    if os.name == 'nt': comando.insert(3, "-screendialogs=no")
        
    try:
        import subprocess
        # Primeira passagem...
        # (MANTENHA O RESTO DO SEU CÓDIGO DAQUI PARA BAIXO IGUAL AO QUE JÁ TINHA)
        # Primeira passagem
        subprocess.run(
            comando, 
            stdout=subprocess.DEVNULL, # Ignora o log gigante que trava o Python
            stderr=subprocess.PIPE, 
            timeout=900, # 15 minutos
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Segunda passagem (para o Índice)
        compilacao = subprocess.run(
            comando, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE, 
            timeout=900, 
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if os.path.exists(arquivo_pdf):
            # Verifica se o PDF não está vazio (corrompido com 0 bytes)
            if os.path.getsize(arquivo_pdf) > 1000: 
                return "sucesso", arquivo_pdf
            
        arquivo_log = os.path.join(diretorio_base, f"{nome_base}.log")
        detalhe_erro = ""
        if os.path.exists(arquivo_log):
            with open(arquivo_log, "r", encoding="utf-8", errors="ignore") as l:
                linhas = l.readlines()
                # Pega as últimas 50 linhas para tentarmos ver o erro real
                detalhe_erro = "\n".join(linhas[-50:]) 
                
        erro_stderr = compilacao.stderr.decode('utf-8', errors='ignore') if compilacao.stderr else ""
        return "erro", f"Log LaTeX:\n{detalhe_erro}\n\nErro Sistema:\n{erro_stderr}"
    except Exception as e:
        return "erro", f"Falha de execução: {str(e)}"