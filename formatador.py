import re
import os
import subprocess
import tempfile
import requests
from bs4 import BeautifulSoup

def raspar_portal_planalto(url):
    """Realiza a extração do texto HTML do portal do Planalto e converte para texto estruturado."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resposta = requests.get(url, headers=headers, timeout=15)
        resposta.encoding = resposta.apparent_encoding or 'utf-8'
        
        if resposta.status_code != 200:
            return f"Erro na requisição: Código HTTP {resposta.status_code}"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        for elem in soup.find_all(['strike', 's', 'del']):
            elem.decompose()
            
        texto = soup.get_text(separator='\n')
        linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        return '\n'.join(linhas)
    except Exception as e:
        return f"Erro ao aceder ao endereço URL: {str(e)}"


def parse_texto_legal(texto_bruto):
    """Transforma o texto bruto em blocos estruturados de artigos e sub-itens."""
    linhas = texto_bruto.split('\n')
    artigos = []
    artigo_atual = None
    
    regex_artigo = re.compile(r'^(Art\.\s*\d+[\w\-]*°?[\w\-]*)\s*[\.\-–—]?\s*(.*)', re.IGNORECASE)
    regex_paragrafo = re.compile(r'^(§\s*\d+°?|Parágrafo\s+único)\s*[\.\-–—]?\s*(.*)', re.IGNORECASE)
    regex_inciso = re.compile(r'^(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))\s*[\.\-–—]\s*(.*)', re.IGNORECASE)
    regex_alinea = re.compile(r'^([a-z])\)\s*(.*)')

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        match_art = regex_artigo.match(linha)
        if match_art:
            if artigo_atual:
                artigos.append(artigo_atual)
            artigo_atual = {
                'artigo': {'nome': match_art.group(1), 'resto': match_art.group(2)},
                'conteudo': []
            }
            continue

        if artigo_atual:
            match_par = regex_paragrafo.match(linha)
            if match_par:
                artigo_atual['conteudo'].append({'tipo': 'PARAGRAFO', 'nome': match_par.group(1), 'resto': match_par.group(2)})
                continue

            match_inc = regex_inciso.match(linha)
            if match_inc and len(match_inc.group(1)) > 0:
                artigo_atual['conteudo'].append({'tipo': 'INCISO', 'nome': match_inc.group(1), 'resto': match_inc.group(4)})
                continue

            match_ali = regex_alinea.match(linha)
            if match_ali:
                artigo_atual['conteudo'].append({'tipo': 'ALINEA', 'nome': match_ali.group(1), 'resto': match_ali.group(2)})
                continue

            artigo_atual['conteudo'].append({'tipo': 'TEXTO', 'nome': '', 'resto': linha})

    if artigo_atual:
        artigos.append(artigo_atual)

    return artigos


def filtrar_artigos(artigos_brutos_totais, anos_destaque=None):
    """Filtra artigos com base nos anos selecionados ou mantém todos se VADE COMPLETO estiver ativo."""
    if not anos_destaque:
        anos_destaque = ['2024', '2025', '2026']
        
    anos_alvo = [str(a).upper() for a in anos_destaque]
    modo_completo = "VADE COMPLETO" in anos_alvo

    if modo_completo:
        return artigos_brutos_totais

    regex_anos = '|'.join([a for a in anos_alvo if a != "VADE COMPLETO"])
    artigos_filtrados = []

    for b in artigos_brutos_totais:
        texto_caput = b['artigo'].get('nome', '') + " " + b['artigo'].get('resto', '')
        caput_tem_ano = any(ano in texto_caput for ano in anos_alvo if ano != "VADE COMPLETO")
        
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
                
                if any(ano in texto_c for ano in anos_alvo if ano != "VADE COMPLETO") or (caput_tem_ano and is_pena):
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
            
        b_copia = dict(b)
        b_copia['conteudo'] = sub_itens_alterados
        artigos_filtrados.append(b_copia)

    return artigos_filtrados


def escapar_latex(texto):
    """Escapa caracteres especiais do LaTeX."""
    substituicoes = {
        '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_',
        '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', '\\': r'\textbackslash{}'
    }
    regex = re.compile('|'.join(re.escape(k) for k in substituicoes.keys()))
    return regex.sub(lambda m: substituicoes[m.group(0)], str(texto))


def gerar_codigo_latex(fila_compilacao, anos_destaque):
    """Gera o código fonte LaTeX para compilação do documento."""
    modo_completo = "VADE COMPLETO" in [str(a).upper() for a in anos_destaque]
    
    latex = r"""\documentclass[10pt,a4paper,twocolumn]{article}
\usepackage[utf8]{utf8}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[pt-BR]{babel}
\usepackage[margin=1.5cm,top=2cm,bottom=2cm]{geometry}
\usepackage{xcolor}
\usepackage{tcolorbox}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{fancyhdr}

\definecolor{primary}{HTML}{1E293B}
\definecolor{accent}{HTML}{2563EB}
\definecolor{bgbox}{HTML}{F8FAFC}

\pagestyle{fancy}
\fancyhf{}
\rhead{\textcolor{gray}{\small Vade Mecum LegalTech}}
\lhead{\textcolor{gray}{\small Compilação de Legislação}}
\cfoot{\thepage}

\begin{document}
"""

    for nome_lei, texto_bruto in fila_compilacao:
        latex += f"\\section*{{\\centering \\color{{primary}} {escapar_latex(nome_lei)}}}\n"
        latex += "\\hrule\\vspace{0.3cm}\n\n"
        
        artigos_brutos = parse_texto_legal(texto_bruto)
        artigos_processados = filtrar_artigos(artigos_brutos, anos_destaque)
        
        for art in artigos_processados:
            caput_nome = escapar_latex(art['artigo']['nome'])
            caput_resto = escapar_latex(art['artigo']['resto'])
            
            if modo_completo:
                latex += f"\\textbf{{{caput_nome}}} {caput_resto}\n\n"
            else:
                latex += f"\\begin{{tcolorbox}}[colback=bgbox,colframe=accent,arc=2pt,outer arc=2pt,top=2pt,bottom=2pt,left=4pt,right=4pt]\n"
                latex += f"\\textbf{{{caput_nome}}} {caput_resto}\n"
                latex += f"\\end{{tcolorbox}}\n\n"
                
            for sub in art['conteudo']:
                tipo = sub['tipo']
                nome = escapar_latex(sub.get('nome', ''))
                resto = escapar_latex(sub.get('resto', ''))
                
                if tipo == 'PARAGRAFO':
                    latex += f"\\noindent \\textbf{{{nome}}} {resto}\\\\ \n"
                elif tipo == 'INCISO':
                    latex += f"\\indent \\textbf{{{nome}}} - {resto}\\\\ \n"
                elif tipo == 'ALINEA':
                    latex += f"\\indent\\indent \\textbf{{{nome}}}) {resto}\\\\ \n"
                else:
                    latex += f"\\noindent {resto}\\\\ \n"
            latex += "\\vspace{0.2cm}\n"

    latex += r"\end{document}"
    return latex


def compilar_pdf(fila_compilacao, nome_base="VadeMecum_Minerado", anos_destaque=None):
    """Compila o documento em PDF utilizando pdflatex."""
    if anos_destaque is None:
        anos_destaque = ["VADE COMPLETO"]
        
    codigo_tex = gerar_codigo_latex(fila_compilacao, anos_destaque)
    
    diretorio_temp = tempfile.mkdtemp()
    caminho_tex = os.path.join(diretorio_temp, f"{nome_base}.tex")
    caminho_pdf = os.path.join(diretorio_temp, f"{nome_base}.pdf")
    
    with open(caminho_tex, "w", encoding="utf-8") as f:
        f.write(codigo_tex)
        
    try:
        processo = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", diretorio_temp, caminho_tex],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        if os.path.exists(caminho_pdf):
            return "sucesso", caminho_pdf
        else:
            return "erro", processo.stdout + "\n" + processo.stderr
    except Exception as e:
        return "erro", str(e)
