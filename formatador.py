import re
import os
import io
import unicodedata
import subprocess
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ==========================================
# 1. SCRAPER DE DADOS
# ==========================================
def raspar_portal_planalto(url):
    try:
        url_limpa = str(url).strip().replace('"', '').replace("'", "").replace('`', '')
        url_limpa = "".join(url_limpa.split())
        
        if not url_limpa.lower().startswith("http"):
            return f"Erro: A URL fornecida não é válida: '{url_limpa}'"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resposta = requests.get(url_limpa, headers=headers, timeout=20)
        resposta.encoding = 'utf-8' if resposta.encoding not in ['ISO-8859-1', 'iso-8859-1'] else 'iso-8859-1'
        
        if resposta.status_code != 200:
            return f"Erro: Status Code: {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        linhas_texto = [p.get_text().strip() for p in soup.find_all(['p', 'span', 'font']) if p.get_text().strip()]
        return "\n".join(linhas_texto) if linhas_texto else "Erro: Não foi possível extrair dados."
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

# ==========================================
# 2. MOTOR EXCEL (NOVA FUNCIONALIDADE)
# ==========================================
def processar_texto_para_dataframe(texto_bruto, diploma_legal, apenas_recentes=False, anos_destaque=None):
    """
    Estrutura os dados na tabela: DIPLOMA LEGAL | DISPOSITIVO | TEXTO
    Agrupa Caput + Parágrafos + Incisos + Alíneas numa única célula por artigo.
    """
    years = ['2024', '2025', '2026'] if anos_destaque is None else [str(a) for a in anos_destaque]
    padrao_anos = re.compile(r'\b(' + '|'.join(years) + r')\b')
    padrao_artigo = re.compile(r'^(Art\.\s*\d+[\w\-°º]*\.?)', re.IGNORECASE)

    linhas = texto_bruto.split('\n')
    artigos_extraidos = []
    artigo_atual = None
    texto_acumulado = []
    tem_ano_recente = False

    for linha in linhas:
        linha = linha.strip()
        if not linha or "googleusercontent" in linha or "immersive_entry" in linha:
            continue

        match_art = padrao_artigo.match(linha)
        
        if match_art:
            if artigo_atual:
                if not apenas_recentes or tem_ano_recente:
                    artigos_extraidos.append({
                        "DIPLOMA LEGAL": diploma_legal,
                        "DISPOSITIVO": artigo_atual,
                        "TEXTO": "\n".join(texto_acumulado)
                    })
            
            artigo_atual = match_art.group(1).upper()
            texto_acumulado = [linha]
            tem_ano_recente = bool(padrao_anos.search(linha))
        else:
            if artigo_atual:
                texto_acumulado.append(linha)
                if padrao_anos.search(linha):
                    tem_ano_recente = True

    if artigo_atual and (not apenas_recentes or tem_ano_recente):
        artigos_extraidos.append({
            "DIPLOMA LEGAL": diploma_legal,
            "DISPOSITIVO": artigo_atual,
            "TEXTO": "\n".join(texto_acumulado)
        })

    return pd.DataFrame(artigos_extraidos)

def gerar_buffer_excel(df):
    """Gera o arquivo .xlsx em memória para download no Streamlit."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Base_Planalto')
    output.seek(0)
    return output

# ==========================================
# 3. MOTOR LATEX / PDF (MANTIDO INTACTO)
# ==========================================
def escapar_caracteres_latex(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFC', texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch)[0] != "C" or ch == '\n')
    
    texto = texto.replace('—', '-').replace('–', '-').replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    texto = texto.replace('\\', r'\textbackslash{}')
    texto = texto.replace('$', r'\$').replace('%', r'\%').replace('&', r'\&')
    texto = texto.replace('#', r'\#').replace('_', r'\_').replace('{', r'\{')
    texto = texto.replace('}', r'\}').replace('^', r'\^{}').replace('~', r'\~{}')
    return texto

def formatar_codigo_penal_para_latex(texto_bruto, anos_destaque=None):
    years = ['2024', '2025', '2026'] if anos_destaque is None else [str(a) for a in anos_destaque]
    padrao_anos = re.compile(r'\b(' + '|'.join(years) + r')\b')
    linhas = texto_bruto.split('\n')
    
    documento_latex = [
        r"\documentclass[10pt,a4paper,twocolumn]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[brazilian]{babel}",
        r"\usepackage[top=1.8cm,bottom=1.8cm,left=1.2cm,right=1.2cm]{geometry}",
        r"\usepackage[most]{tcolorbox}",
        r"\sloppy",
        r"\newtcolorbox{notalegislativa}{colback=gray!6,colframe=gray!50,arc=0.8mm,boxrule=0.5pt,left=1.5mm,right=1.5mm,top=1mm,bottom=1mm}",
        r"\title{\textbf{Vade Mecum: Novidades Legislativas}}",
        r"\author{Laboratório LAPEJURI}",
        r"\date{\today}",
        r"\begin{document}",
        r"\maketitle",
        r"\newpage",
        ""
    ]

    articles = []
    current_article = {"header": None, "paragraphs": [], "has_year": False}

    for linha in linhas:
        linha = linha.strip()
        if not linha or "googleusercontent" in linha or "immersive_entry" in linha: continue
        
        if re.match(r'^Art\.\s*', linha):
            if current_article["header"] or current_article["paragraphs"]:
                articles.append(current_article)
            current_article = {"header": linha, "paragraphs": [], "has_year": bool(padrao_anos.search(linha))}
        else:
            if current_article["header"] is None: continue
            has_yr = bool(padrao_anos.search(linha))
            current_article["paragraphs"].append({"text": linha, "has_year": has_yr})
            if has_yr: current_article["has_year"] = True

    if current_article["header"] or current_article["paragraphs"]:
        articles.append(current_article)

    for art in articles:
        if not art["has_year"]: continue
        
        paragrafos_recentes = [p for p in art["paragraphs"] if p["has_year"]]
        header_tem_ano = bool(padrao_anos.search(art["header"]))
        
        if not paragrafos_recentes and not header_tem_ano: continue

        header_esc = escapar_caracteres_latex(art["header"])
        documento_latex.append(f"\n\\subsection*{{{header_esc}}}")
        documento_latex.append("\\begin{notalegislativa}")

        if not header_tem_ano:
            documento_latex.append(r"\textit{\small [Exibindo apenas trechos recentes modificados:]} \\")

        for i, p in enumerate(paragrafos_recentes):
            texto_esc = escapar_caracteres_latex(p["text"])
            sufixo = " \\\\" if i < len(paragrafos_recentes) - 1 else ""
            documento_latex.append(f"\\noindent {texto_esc}{sufixo}")
            
        documento_latex.append("\\end{notalegislativa}")

    documento_latex.append("\n\\end{document}")
    return "\n".join(documento_latex)

def compilar_pdf(texto_bruto, nome_base="VadeMecum_Minerado", anos_destaque=None):
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    arquivo_tex = os.path.join(diretorio_atual, f"{nome_base}.tex")
    arquivo_pdf = os.path.join(diretorio_atual, f"{nome_base}.pdf")
    
    codigo_tex = formatar_codigo_penal_para_latex(texto_bruto, anos_destaque)
    
    with open(arquivo_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    comando = [
        "pdflatex", 
        "-interaction=nonstopmode", 
        "-halt-on-error",
        f"-output-directory={diretorio_atual}", 
        arquivo_tex
    ]
    
    try:
        compilacao = subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            encoding="utf-8", 
            errors="ignore", 
            timeout=50,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if os.path.exists(arquivo_pdf):
            return "sucesso", arquivo_pdf
            
        arquivo_log = os.path.join(diretorio_atual, f"{nome_base}.log")
        erro_log = ""
        if os.path.exists(arquivo_log):
            with open(arquivo_log, "r", encoding="utf-8", errors="ignore") as l:
                erro_log = "\n".join(l.readlines()[-25:])
        return "erro", f"LaTeX Log:\n{erro_log}\n\nTerminal Output:\n{compilacao.stdout}"
    except Exception as e:
        return "erro", f"Falha crítica no Windows: {str(e)}"