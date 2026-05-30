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

def formatar_codigo_penal_para_latex(texto_bruto, anos_destaque=None):
    if anos_destaque is None:
        anos_destaque = ['2024', '2025', '2026']
    
    anos_str = [str(ano) for ano in anos_destaque]
    padrao_anos = re.compile(r'\b(' + '|'.join(anos_str) + r')\b')
    
    linhas = limpar_linhas_duplicadas(texto_bruto)
    
    documento_latex = [
        r"\documentclass[10pt,a4paper,twocolumn]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[brazilian]{babel}",
        r"\usepackage[top=2cm,bottom=2cm,left=1.2cm,right=1.2cm]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage[most]{tcolorbox}",
        r"\usepackage{titlesec}",
        r"\sloppy",
        "",
        r"\newtcolorbox{notalegislativa}{colback=gray!8,colframe=gray!60,arc=1mm,boxrule=0.6pt,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm}",
        "",
        r"\title{\textbf{Vade Mecum de Novidades Legislativas}}",
        r"\author{Laboratório de Pesquisa Empírica, Jurimetria e IA}",
        r"\date{\today}",
        r"\begin{document}",
        r"\maketitle",
        r"\newpage",
        ""
    ]

    articles = []
    current_article = {"header": None, "headings": [], "paragraphs": [], "has_year": False}
    active_headings = []

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

    for art in articles:
        if not art["has_year"]:
            continue
        
        # FILTRO DE CORTE CIRÚRGICO INTERNO
        paragrafos_recentes = [p for p in art["paragraphs"] if p["has_year"]]
        header_tem_ano = bool(padrao_anos.search(art["header"]))
        
        if not paragrafos_recentes and not header_tem_ano:
            continue

        for heading in art["headings"]:
            if heading not in printed_headings:
                heading_esc = escapar_caracteres_latex(heading)
                buffer_linhas.append(f"\n\\begin{{center}}\\vspace{{0.1cm}}\\textbf{{\\small {heading_esc}}}\\end{{center}}\n")
                printed_headings.add(heading)
        
        match_art = re.match(r'^Art\.\s*([0-9]+[-A-Z]*)\s*[\.-]?\s*(.*)', art["header"])
        if match_art:
            art_num = match_art.group(1)
            art_texto = match_art.group(2)
            buffer_linhas.append(f"\n\\subsection*{{Art. {art_num}}}")
            buffer_linhas.append("\\begin{notalegislativa}")
            
            # Só exibe o caput se ele contiver a mudança recente explicita
            if header_tem_ano and art_texto:
                art_texto_esc = escapar_caracteres_latex(art_texto)
                buffer_linhas.append(f"{art_texto_esc} \\\\")
        else:
            header_esc = escapar_caracteres_latex(art["header"])
            buffer_linhas.append(f"\n\\subsection*{{{header_esc}}}")
            buffer_linhas.append("\\begin{notalegislativa}")

        # Adiciona APENAS as linhas que possuem o ano alvo dentro da caixa cinza
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

def compilar_pdf(texto_bruto, nome_base="VadeMecum_Minerado", anos_destaque=None):
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    arquivo_tex = os.path.join(diretorio_atual, f"{nome_base}.tex")
    arquivo_pdf = os.path.join(diretorio_atual, f"{nome_base}.pdf")
    
    # Gera o código LaTeX com o filtro estrito (2024-2026)
    codigo_tex = formatar_codigo_penal_para_latex(texto_bruto, anos_destaque)
    
    with open(arquivo_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    # COMANDO BLINDADO PARA WINDOWS (Força o MiKTeX a instalar pacotes sem abrir janelas pop-up)
    comando = [
        "pdflatex", 
        "-interaction=nonstopmode", 
        "-halt-on-error",
        "-screendialogs=no",
        f"-output-directory={diretorio_atual}", 
        arquivo_tex
    ]
    
    try:
        # Executa a compilação nativa do Windows através do Python
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
            
        # Se falhar, captura o arquivo .log que o LaTeX gera para sabermos o motivo real
        arquivo_log = os.path.join(diretorio_atual, f"{nome_base}.log")
        detalhe_erro = ""
        if os.path.exists(arquivo_log):
            with open(arquivo_log, "r", encoding="utf-8", errors="ignore") as l:
                # Pega as últimas 30 linhas do log (onde o erro real do LaTeX fica guardado)
                detalhe_erro = "\n".join(l.readlines()[-30:])
                
        return "erro", f"Erro na compilação do LaTeX no Windows.\n\nTrecho do Log:\n{detalhe_erro}\n\nSaída do terminal:\n{compilacao.stdout}"
        
    except Exception as e:
        return "erro", f"Falha ao acionar o subprocesso pdflatex no Windows: {str(e)}"