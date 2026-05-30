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
        linhas_texto = [p.get_text().strip() for p in soup.find_all(['p', 'span', 'font']) if p.get_text().strip()]
        return "\n".join(linhas_texto) if linhas_texto else "Erro: Não foi possível extrair dados."
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

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

def formatar_codigo_penal_para_latex(lista_leis, anos_destaque=None):
    """
    Agora recebe lista_leis: [("Nome da Lei 1", "Texto Bruto 1"), ("Nome da Lei 2", "Texto Bruto 2")]
    """
    years = ['2024', '2025', '2026'] if anos_destaque is None else [str(a) for a in anos_destaque]
    padrao_anos = re.compile(r'\b(' + '|'.join(years) + r')\b')
    
    documento_latex = [
        r"\documentclass[9pt,a4paper,twocolumn]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[brazilian]{babel}",
        r"\usepackage[top=1.5cm,bottom=1.5cm,left=1.0cm,right=1.0cm]{geometry}",
        r"\usepackage[most]{tcolorbox}",
        r"\usepackage{enumitem}",
        r"\sloppy",
        r"\newtcolorbox{caixaartigo}[1]{",
        r"  colback=gray!4,colframe=slateheading!60!black,coltitle=white,",
        r"  fonttitle=\bfseries\small,title={#1},",
        r"  arc=1.0mm,boxrule=0.6pt,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,",
        r"  before skip=3mm,after skip=3mm,breakable",
        r"}",
        r"\definecolor{slateheading}{rgb}{0.18, 0.24, 0.35}",
        r"\definecolor{lawtitle}{rgb}{0.1, 0.15, 0.25}",
        r"\title{\textbf{\Large Vade Mecum de Novidades Legislativas}\\\small{Compilação Estruturada LAPEJURI}}",
        r"\author{\small Laboratório de Pesquisa Empírica, Jurimetria e IA}",
        r"\date{\small\today}",
        r"\begin{document}",
        r"\maketitle",
        r"\setlength{\columnsep}{18pt}",
    ]

    reg_livro = re.compile(r'^(LIVRO\s+[IVXLCDM]+)', re.IGNORECASE)
    reg_titulo = re.compile(r'^(TÍTULO\s+[IVXLCDM]+)', re.IGNORECASE)
    reg_capitulo = re.compile(r'^(CAPÍTULO\s+[IVXLCDM]+)', re.IGNORECASE)
    reg_artigo = re.compile(r'^Art\.\s*([\d\w-]+)', re.IGNORECASE)

    # LOOP PRINCIPAL: Processa cada lei separadamente
    for nome_lei, texto_bruto in lista_leis:
        
        # Reseta os memorizadores de hierarquia para a nova lei não herdar da anterior
        livro_atual = ""
        titulo_atual = ""
        capitulo_atual = ""
        artigos_processados = []
        artigo_foco = None
        
        linhas = texto_bruto.split('\n')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha or "googleusercontent" in linha or "immersive_entry" in linha: continue
            
            if reg_livro.match(linha):
                livro_atual = linha; continue
            if reg_titulo.match(linha):
                titulo_atual = linha; capitulo_atual = ""; continue
            if reg_capitulo.match(linha):
                capitulo_atual = linha; continue
                
            if reg_artigo.match(linha):
                if artigo_foco:
                    artigos_processados.append(artigo_foco)
                artigo_foco = {
                    "livro": livro_atual, "titulo": titulo_atual, "capitulo": capitulo_atual,
                    "caput": linha, "paragrafos": [], "relevante": bool(padrao_anos.search(linha))
                }
            else:
                if artigo_foco is None: continue
                tem_ano = bool(padrao_anos.search(linha))
                artigo_foco["paragrafos"].append({"texto": linha, "relevante": tem_ano})
                if tem_ano: artigo_foco["relevante"] = True

        if artigo_foco: artigos_processados.append(artigo_foco)

        # Filtra para ver se a lei tem pelo menos 1 artigo modificado nos anos
        artigos_validos = [art for art in artigos_processados if art["relevante"]]
        
        if artigos_validos:
            # Imprime o Título Gigante da Lei no PDF
            nome_lei_esc = escapar_caracteres_latex(nome_lei)
            documento_latex.append(f"\n\\vspace{{5mm}}")
            documento_latex.append(f"\\begin{{center}}\\color{{lawtitle}}\\Large\\textbf{{{nome_lei_esc}}}\\end{{center}}")
            documento_latex.append(f"\\vspace{{2mm}}\\hrule\\vspace{{3mm}}")

            ultimo_livro_impresso = ""
            ultimo_titulo_impresso = ""
            ultimo_capitulo_impresso = ""

            for art in artigos_validos:
                if art["livro"] and art["livro"] != ultimo_livro_impresso:
                    documento_latex.append(f"\n\\section*{{\\centering \\color{{slateheading}}\\normalsize {escapar_caracteres_latex(art['livro'])}}}")
                    ultimo_livro_impresso = art["livro"]
                    
                if art["titulo"] and art["titulo"] != ultimo_titulo_impresso:
                    documento_latex.append(f"\n\\subsection*{{\\centering \\color{{slateheading}}\\small {escapar_caracteres_latex(art['titulo'])}}}")
                    ultimo_titulo_impresso = art["titulo"]
                    
                if art["capitulo"] and art["capitulo"] != ultimo_capitulo_impresso:
                    documento_latex.append(f"\n\\subsubsection*{{\\centering \\small \\textit{{{escapar_caracteres_latex(art['capitulo'])}}}}}")
                    ultimo_capitulo_impresso = art["capitulo"]

                match_art = reg_artigo.match(art["caput"])
                num_artigo = f"Artigo {match_art.group(1)}" if match_art else "Artigo"
                
                documento_latex.append(f"\\begin{{caixaartigo}}{{{num_artigo}}}")
                caput_esc = escapar_caracteres_latex(art["caput"])
                documento_latex.append(f"\\textbf{{{caput_esc}}} \\\\[1mm]")
                
                if art["paragrafos"]:
                    documento_latex.append("\\begin{description}[leftmargin=1.5mm, labelindent=0mm, itemsep=1mm]")
                    for p in art["paragrafos"]:
                        p_esc = escapar_caracteres_latex(p["texto"])
                        if p["relevante"]:
                            documento_latex.append(f"\\item[] \\strut {p_esc}")
                        else:
                            documento_latex.append(f"\\item[] \\small \\color{{gray!90}} {p_esc}")
                    documento_latex.append("\\end{description}")
                    
                documento_latex.append("\\end{caixaartigo}\n")

    documento_latex.append("\n\\end{document}")
    return "\n".join(documento_latex)

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