import streamlit as st
import os
import base64
from datetime import datetime
import formatador
import re
import time

st.set_page_config(page_title="LAPEJURI - LegalTech", page_icon="⚖️", layout="wide")
# ... (MANTENHA O SEU CÓDIGO app.py IGUAL ATÉ À ZONA DO BOTÃO INICIAR) ...
MAPA_LEIS = {
    "Código Penal (Decreto-Lei nº 2.848/40)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
    "Código de Processo Penal (Decreto-Lei nº 3.689/41)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689.htm",
    "Lei de Crimes Hediondos (Lei nº 8.072/90)": "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm",
    "Lei de Introdução às Normas do Direito Brasileiro (LINDB)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm",
    "Código Civil (Lei nº 10.406/2002)": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406.htm",
    "Código de Processo Civil (Lei nº 13.105/2015)": "https://www4.planalto.gov.br/legislacao/portal-legis/legislacao-1/codigos-1#wrapper",
    "Código Tributário Nacional (Lei nº 5.172/1967)": "https://www.planalto.gov.br/ccivil_03/leis/l5172.htm",
    "Consolidação das Leis do Trabalho (Decreto-Lei nº 5.430/1943)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
    "Código de Defesa do Consumidor (Lei nº 8.078/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8078.htm",
    "Código Eleitoral (Lei nº 4.737/1965)": "https://www.planalto.gov.br/ccivil_03/leis/l4737.htm",
    "Estatuto da Criança e do Adolescente (Lei nº 12.525/2011)": "https://www.planalto.gov.br/ccivil_03/leis/l8069.htm",
    "Estatuto da Pessoa Idosa (Lei nº 10.741/2003)": "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.741.htm",
    "Estatuto da Igualdade Racial (Lei nº 12.288/2010)": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12288.htm",
    "Estatuto da Pessoa com Deficiência (Lei nº 13.146/2015)": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm",
    "Lei Maria da Penha (Lei nº 11.340/2006)": "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm",
    "Lei de Contravenções Penais (Decreto-Lei nº 3.688/41)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm",
    "Lei de Introdução ao Código Penal (Decreto-Lei nº 3.914/1941)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3914.htm",
    "Lei de Execução Penal (Lei nº 7.210/1984)": "https://www.planalto.gov.br/ccivil_03/leis/l7210.htm",
    "Lei dos Crimes contra a Ordem Tributária (Lei nº 8.137/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8137.htm",
    "Lei de Diretrizes e Bases da Educação (Lei nº 9.394/1996)": "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm",
    "Lei dos Empregados Domésticos (Lei nº 5.810/1972)": "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp150.htm",
    "Regime Jurídico dos Servidores Públicos (Lei nº 8.112/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8112cons.htm",
    "Lei de Licitações e Contratos Administrativos (Lei nº 14.133/2021)": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
}

if "logs" not in st.session_state:
    st.session_state["logs"] = [{"timestamp": datetime.now().strftime("%H:%M:%S"), "texto": "Consola de auditoria inicializada.", "tipo": "Info"}]

def registar_log(texto, tipo):
    hora_atual = datetime.now().strftime("%H:%M:%S")
    st.session_state["logs"].insert(0, {"timestamp": hora_atual, "texto": texto, "tipo": tipo})

st.markdown("<h1 style='text-align: center; color: #1E293B;'>⚖️ Inteligência Documental em Lote - LAPEJURI</h1>", unsafe_allow_html=True)
st.divider()

col_esquerda, col_direita = st.columns([1, 1])

with col_esquerda:
    st.subheader("📥 Configuração da Coleta em Série")
    
    fonte_opcao = st.radio(
        "Como deseja inserir a legislação?", 
        ["Capturar do Portal Planalto (Múltiplos Diplomas)", "Colar Texto Bruto Manuscrito"],
        horizontal=False
    )
    
    lista_final_leis = []
    
    if fonte_opcao == "Capturar do Portal Planalto (Múltiplos Diplomas)":
        leis_selecionadas = st.multiselect(
            "Selecione os Diplomas Cadastrados para processar em série:", 
            options=list(MAPA_LEIS.keys()),
            default=["Código Penal (Decreto-Lei nº 2.848/40)"]
        )
        
        urls_adicionais = st.text_area(
            "Cole URLs adicionais do Planalto (Uma por linha se desejar expandir):",
            placeholder="https://www.planalto.gov.br/..."
        )
        
        # Construindo fila de mineração
        for lei in leis_selecionadas:
            lista_final_leis.append((lei, MAPA_LEIS[lei]))
            
        if urls_adicionais.strip():
            for idx, linha_url in enumerate(urls_adicionais.split("\n")):
                linha_url = linha_url.strip()
                if linha_url:
                    lista_final_leis.append((f"Legislação Adicional Customizada {idx+1}", linha_url))
                    
    elif fonte_opcao == "Colar Texto Bruto Manuscrito":
        texto_entrada = st.text_area("Cole os artigos do Vade Mecum aqui:", height=200)
        if texto_entrada.strip():
            lista_final_leis.append(("Texto Manuscrito Injetado", texto_entrada))

    st.markdown("---")
    st.subheader("📅 Filtro de Destaques")
    
    # NOVAS COLUNAS PARA OS ANOS ALVO
    col_anos1, col_anos2 = st.columns([2, 1])
    
    with col_anos1:
        anos_disponiveis = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]
        anos_selecionados = st.multiselect(
            "Selecione os anos alvo na lista:",
            options=anos_disponiveis,
            default=[2024, 2025, 2026]
        )
        
    with col_anos2:
        anos_extras_texto = st.text_input(
            "Outros anos (Ex: 2018):",
            placeholder="Ex: 2018, 2019"
        )

    # Lógica de fusão dos anos (Menu + Texto Livre)
    anos_finais = list(anos_selecionados)
    if anos_extras_texto.strip():
        anos_extras = re.findall(r'\b\d{4}\b', anos_extras_texto)
        anos_finais.extend([int(a) for a in anos_extras])
        
    # Remove duplicados e ordena
    anos_finais = sorted(list(set(anos_finais)))

    if st.button("🚀 Iniciar Coleta e Compilação Automática", use_container_width=True):
        if not anos_finais:
            st.warning("⚠️ Selecione ou digite pelo menos um ano para servir de filtro de alterações.")
        elif not lista_final_leis:
            st.warning("⚠️ Nenhuma fonte de dados ou URL estruturada foi detectada.")
        else:
            fila_compilacao = []
            
            if fonte_opcao == "Capturar do Portal Planalto (Múltiplos Diplomas)":
                barra_progresso = st.progress(0)
                status_coleta = st.empty()
                total_itens = len(lista_final_leis)
                
                for i, (nome_lei, url_bruta) in enumerate(lista_final_leis):
                    status_coleta.markdown(f"**Minerando ({i+1}/{total_itens}):** {nome_lei}...")
                    
                    extrator = re.search(r'(https?://[^\s\]\)\'"]+)', url_bruta)
                    url_higienizada = extrator.group(1) if extrator else url_bruta.strip()
                    url_higienizada = "".join(url_higienizada.split()).replace('"', '').replace("'", "")
                    
                    registar_log(f"Processando link: {url_higienizada}", "Scraping")
                    texto_extraido = formatador.raspar_portal_planalto(url_higienizada)
                    
                    if texto_extraido.startswith("Erro"):
                        st.error(f"Falha na extração de: {nome_lei}. Detalhe: {texto_extraido}")
                        registar_log(f"Erro em {nome_lei}: {texto_extraido}", "Erro")
                    else:
                        registar_log(f"Conteúdo de {nome_lei} armazenado com sucesso.", "Sucesso")
                        fila_compilacao.append((nome_lei, texto_extraido))
                    
                    barra_progresso.progress((i + 1) / total_itens)
                    time.sleep(2.5)  # Delay para evitar bloqueios
                status_coleta.empty()
                barra_progresso.empty()
            else:
                fila_compilacao = lista_final_leis

            if fila_compilacao:
                with st.spinner("⚙️ Compilando PDF Unificado via MiKTeX (Dupla Passagem para Sumário)..."):
                    registar_log(f"Iniciando montagem do lote com {len(fila_compilacao)} itens.", "Info")
                    
                    # Chamada corrigida e limpa
                    status, resultado = formatador.compilar_pdf(
                        fila_compilacao, 
                        nome_base="VadeMecum_Minerado", 
                        anos_destaque=anos_finais
                    )
                    
                    if status == "sucesso":
                        st.success("🎉 Compilação em lote concluída com sucesso!")
                        registar_log("Documento PDF Multi-Leis gerado com sucesso.", "Sucesso")
                        st.session_state["pdf_pronto"] = resultado
                    else:
                        st.error("🚨 Falha na compilação estrutural do LaTeX.")
                        registar_log("Erro crítico na árvore LaTeX durante compilação.", "Erro")
                        st.text_area("Log Técnico de Erros:", value=resultado, height=200)
            else:
                st.error("Nenhum texto válido pôde ser coletado para compilação.")

with col_direita:
    st.subheader("📄 Painel de Resultados")
    
    if "pdf_pronto" in st.session_state and os.path.exists(st.session_state["pdf_pronto"]):
        caminho_pdf = st.session_state["pdf_pronto"]
        
        with open(caminho_pdf, "rb") as f_pdf:
            dados_pdf = f_pdf.read()
            st.download_button(
                label="📥 Descarregar Vade Mecum Compilado (PDF)",
                data=dados_pdf,
                file_name="VadeMecum_LAPEJURI_Lote.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        import streamlit.components.v1 as components
        import base64

        # 1. Converte os dados binários do PDF para string Base64 (sem quebras de linha)
        base64_pdf = base64.b64encode(dados_pdf).decode('utf-8')
        
        # 2. Constrói o HTML injetando JavaScript para converter Base64 em Blob em tempo de execução
        html_preview = f"""
        <iframe id="pdf-viewer" width="100%" height="580px" style="border:1px solid #64748B; border-radius:8px;"></iframe>
        <script>
            try {{
                var base64Data = "{base64_pdf}";
                var byteCharacters = atob(base64Data);
                var byteNumbers = new Array(byteCharacters.length);
                for (var i = 0; i < byteCharacters.length; i++) {{
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }}
                var byteArray = new Uint8Array(byteNumbers);
                var blob = new Blob([byteArray], {{type: 'application/pdf'}});
                var blobUrl = URL.createObjectURL(blob);
                document.getElementById('pdf-viewer').src = blobUrl;
            }} catch(e) {{
                document.write('<p style="font-family:sans-serif; color:#64748B; font-size:14px;">Não foi possível carregar a pré-visualização interativa. Por favor, utilize o botão de descarregar acima para abrir o Vade Mecum.</p>');
            }}
        </script>
        """
        
        # 3. Renderiza o visualizador isolado num ambiente seguro (fura o bloqueio do Edge/Chrome)
        components.html(html_preview, height=600)