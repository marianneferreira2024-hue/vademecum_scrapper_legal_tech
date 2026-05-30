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
            return f"Erro: A URL fornecida não é válida: '{url_limpa}'"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resposta = requests.get(url_limpa, headers=headers, timeout=20)
        
        if resposta.encoding in ['ISO-8859-1', 'iso-8859-1']:
            resposta.encoding = 'iso-8859-1'
        else:
            resposta.encoding = 'utf-8'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        paragrafos = soup.find_all(['p', 'span', 'font'])
        linhas_texto = []
        
        for p in paragrafos:
            texto_linha = p.get_text().strip()
            if texto_linha:
                texto_linha = re.sub(r'\s+', ' ', texto_linha)
                linhas_texto.append(texto_linha)
                
        if not linhas_texto:
            return "Erro: O scraper não conseguiu extrair blocos de texto."
            
        return "\n".join(linhas_texto)
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

def limpar_texto_para_latex(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFC', texto)
    texto = texto.replace('\u0096', '-').replace('\x96', '-').replace('—', '-').replace('–', '-')
    texto = texto.replace('\x93', '"').replace('\x94', '"').replace('\u0093', '"').replace('\u0094', '"')
    texto = texto.replace('“', '"').replace('”', '"').replace('\x91', "'").replace('\x92', "'")
    texto = texto.replace('‘', "'").replace('’', "'").replace('\xa0', ' ')
    return texto

def escapar_caracteres_latex(texto):
    """Blindagem total contra caracteres especiais que quebram o compilador LaTeX."""
    if not texto:
        return ""
    texto = texto.replace('\\', r'\textbackslash{}')
    texto = texto.replace('$', r'\$')
    texto = texto.replace('%', r'\%')
    texto = texto.replace('&', r'\&')
    texto = texto.replace('#', r'\#')
    texto = texto.replace('_', r'\_')
    texto = texto.replace('{', r'\{')
    texto = texto.replace('}', r'\}')
    texto = texto.replace('^', r'\^{}')
    texto = texto.replace('~', r'\~{}')
    return texto

def limpar_linhas_duplicadas(texto_bruto):
    texto_sanitizado = limpar_texto_para_latex(texto_bruto)
    linhas = texto_sanitizado.split('\n')
    linhas_limpas = []
    for copy_linha in linhas:
        if "googleusercontent.com" in copy_linha or "immersive_entry_chip" in copy_linha:
            continue
        linha_tratada = re.sub(r'^↳\s*\[Nota\]\s*', '', copy_linha).strip()
        if not linha_tratada or (linhas_limpas and linhas_limpas[-1] == linha_tratada):
            continue
        linhas_limpas.append(linha_tratada)
    return linhas_limpas

def formatar_codigo_penal_para_latex(lista_leis, anos_destaque=None):
    """
    Recebe uma lista de tuplas: [("Nome da Lei", "Texto Bruto"), ...]
    Retorna o código LaTeX unificado e blindado contra estouro de margens.
    """
    if anos_destaque is None:
        anos_destaque = ['2024', '2025', '2026']
    
    anos_str = [str(ano) for ano in anos_destaque]
    padrao_anos = re.compile(r'\b(' + '|'.join(anos_str) + r')\b')
    
    documento_latex = [
        r"\usepackage[brazilian]{babel}",
        r"\usepackage{lmodern}", # RESOLVE O ERRO: Carrega fontes escaláveis
        r"\usepackage[top=2cm,bottom=2cm,left=1.2cm,right=1.2cm]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage[most]{tcolorbox}",
        r"\usepackage{titlesec}",
        r"\usepackage[protrusion=true,expansion=false]{microtype}", # Impede o LaTeX de tentar esticar as letras
        "",
        # Caixa blindada contra estouro e configurada para quebrar páginas de forma limpa
        r"\newtcolorbox{notalegislativa}{",
        r"  enhanced, width=\linewidth, breakable,",
        r"  colback=gray!8,colframe=gray!60,arc=1mm,boxrule=0.6pt,",
        r"  left=2mm,right=2mm,top=1.5mm,bottom=1.5mm",
        r"}",
        "",
        r"\addto\captionsbrazilian{\renewcommand{\contentsname}{Sumário das Novidades Legislativas}}",
        "",
        r"\title{\textbf{\Large Vade Mecum de Novidades Legislativas}\\{\small Compilação Estruturada LAPEJURI}}",
        r"\author{\small Laboratório de Pesquisa Empírica, Jurimetria e IA}",
        r"\date{\small\today}",
        r"\begin{document}",
        r"\maketitle",
        "",
        r"\tableofcontents",  # Inserção Dinâmica do Sumário
        r"\vspace{0.5cm}\hrule\vspace{0.5cm}",
        ""
    ]

    # Processamento sequencial e isolado por diploma
    for nome_lei, texto_bruto in lista_leis:
        linhas = limpar_linhas_duplicadas(texto_bruto)
        
        articles = []
        current_article = {"header": None, "headings": [], "paragraphs": [], "has_year": False}
        active_headings = []
        
        # Estrutura interna para evitar vazamentos entre Leis diferentes
        for linha in linhas:
            if any(t in linha for t in ["TÍTULO", "CAPÍTULO", "SEÇÃO"]):
                if "TÍTULO" in linha: active_headings = [linha]
                elif "CAPÍTULO" in linha: active_headings = [h for h in active_headings if "TÍTULO" in h] + [linha]
                elif "SEÇÃO" in linha: active_headings = [h for h in active_headings if "TÍTULO" in h or "CAPÍTULO" in h] + [linha]
            elif re.match(r'^Art\.\s*', linha):
                if current_article["header"] or current_article["paragraphs"]:
                    articles.append(current_article)
                current_article = {
                    "header": linha, 
                    "headings": list(active_headings), 
                    "paragraphs": [], 
                    "has_year": bool(padrao_anos.search(linha))
                }
            else:
                if current_article["header"] is None: continue
                has_yr = bool(padrao_anos.search(linha))
                current_article["paragraphs"].append({"text": linha, "has_year": has_yr})
                if has_yr:
                    current_article["has_year"] = True

        if current_article["header"] or current_article["paragraphs"]:
            articles.append(current_article)

        buffer_linhas = []
        printed_headings = set()
        
        # Mapeia se esta lei específica possui atualizações válidas
        lei_tem_conteudo = any(
            art["has_year"] and ([p for p in art["paragraphs"] if p["has_year"]] or bool(padrao_anos.search(art["header"])))
            for art in articles
        )
        
        if lei_tem_conteudo:
            nome_lei_esc = escapar_caracteres_latex(nome_lei)
            # Alimenta o Sumário com o Nome da Lei
            buffer_linhas.append(f"\n\\addcontentsline{{toc}}{{section}}{{{nome_lei_esc}}}")
            buffer_linhas.append(f"\n\\begin{{center}}\\vspace{{0.3cm}}\\large\\textbf{{\\color{{blue!40!black}}{nome_lei_esc}}}\\end{{center}}\\nopagebreak\n")

            for art in articles:
                if not art["has_year"]:
                    continue
                
                paragrafos_recentes = [p for p in art["paragraphs"] if p["has_year"]]
                header_tem_ano = bool(padrao_anos.search(art["header"]))
                
                if not paragrafos_recentes and not header_tem_ano:
                    continue

                for heading in art["headings"]:
                    if heading not in printed_headings:
                        heading_esc = escapar_caracteres_latex(heading)
                        buffer_linhas.append(f"\n\\begin{{center}}\\vspace{{0.1cm}}\\textbf{{\\small {heading_esc}}}\\end{{center}}\\nopagebreak\n")
                        # Alimenta o subnível do sumário para organização indexada
                        buffer_linhas.append(f"\\addcontentsline{{toc}}{{subsection}}{{{heading_esc}}}")
                        printed_headings.add(heading)
                
                match_art = re.match(r'^Art\.\s*([0-9]+[-A-Z]*)\s*[\.-]?\s*(.*)', art["header"])
                if match_art:
                    art_num = match_art.group(1)
                    art_texto = match_art.group(2)
                    buffer_linhas.append(f"\n\\subsection*{{Art. {art_num}}}")
                    buffer_linhas.append("\\begin{notalegislativa}")
                    
                    if header_tem_ano and art_texto:
                        art_texto_esc = escapar_caracteres_latex(art_texto)
                        buffer_linhas.append(f"{art_texto_esc} \\\\")
                else:
                    header_esc = escapar_caracteres_latex(art["header"])
                    buffer_linhas.append(f"\n\\subsection*{{{header_esc}}}")
                    buffer_linhas.append("\\begin{notalegislativa}")

                for p in paragrafos_recentes:
                    linha_esc = escapar_caracteres_latex(p["text"])
                    if p["text"].startswith("Pena"):
                        linha_formatada = re.sub(r'^\s*Pena\s*[-–]\s*(.*)', r'\\noindent \\textbf{Pena -} \1', linha_esc)
                        buffer_linhas.append(f"    {linha_formatada} \\\\")
                    else:
                        buffer_linhas.append(f"\\noindent {linha_esc} \\\\")
                
                buffer_linhas.append("\\end{notalegislativa}")

            documento_latex.extend(buffer_linhas)

    documento_latex.append("\n\\end{document}")
    return "\n".join(documento_latex)

def compilar_pdf(lista_leis, nome_base="VadeMecum_Minerado", anos_destaque=None):
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    arquivo_tex = os.path.join(diretorio_atual, f"{nome_base}.tex")
    arquivo_pdf = os.path.join(diretorio_atual, f"{nome_base}.pdf")
    
    codigo_tex = formatar_codigo_penal_para_latex(lista_leis, anos_destaque)
    
    with open(arquivo_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    comando = [
        "pdflatex", 
        "-interaction=nonstopmode", 
        "-halt-on-error",
        "-screendialogs=no",
        f"-output-directory={diretorio_atual}", 
        arquivo_tex
    ]
    
    try:
        # PRIMEIRA PASSAGEM: Descobre a localização dos títulos e cria os arquivos auxiliares (.toc)
        subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            encoding="utf-8", 
            errors="ignore", 
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # SEGUNDA PASSAGEM: Monta o sumário físico apontando para os números de páginas corretos
        compilacao = subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            encoding="utf-8", 
            errors="ignore", 
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if os.path.exists(arquivo_pdf):
            return "sucesso", arquivo_pdf
            
        arquivo_log = os.path.join(diretorio_atual, f"{nome_base}.log")
        detalhe_erro = ""
        if os.path.exists(arquivo_log):
            with open(arquivo_log, "r", encoding="utf-8", errors="ignore") as l:
                detalhe_erro = "\n".join(l.readlines()[-30:])
                
        return "erro", f"Erro na compilação do LaTeX.\n\nTrecho do Log:\n{detalhe_erro}\n\nSaída do terminal:\n{compilacao.stdout}"
        
    except Exception as e:
        return "erro", f"Falha ao acionar o subprocesso pdflatex: {str(e)}"