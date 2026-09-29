import streamlit as st
import os
import base64
from datetime import datetime
import formatador
import re
import time

# Tenta importar o minerador específico da Constituição, se existente
try:
    from scraper_constituicao import baixar_constituicao_completa
except ImportError:
    def baixar_constituicao_completa():
        return formatador.raspar_portal_planalto("https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm")

st.set_page_config(page_title="VADE ATUALIZADO LegalTech", page_icon="⚖️️", layout="wide")

MAPA_LEIS = {
    "Constituição Federal (1988)": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
    "Código Penal (Decreto-Lei nº 2.848/40)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
    "Código de Processo Penal (Decreto-Lei nº 3.689/41)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689.htm",
    "Lei de Crimes Hediondos (Lei nº 8.072/90)": "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm",
    "Lei de Introdução às Normas do Direito Brasileiro (LINDB)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm",
    "Código Civil (Lei nº 10.406/2002)": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406.htm",
    "Código de Processo Civil (Lei nº 13.105/2015)": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm",
    "Código Tributário Nacional (Lei nº 5.172/1967)": "https://www.planalto.gov.br/ccivil_03/leis/l5172.htm",
    "Consolidação das Leis do Trabalho (Decreto-Lei nº 5.430/1943)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
    "Código de Defesa do Consumidor (Lei nº 8.078/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8078.htm",
    "Código Eleitoral (Lei nº 4.737/1965)": "https://www.planalto.gov.br/ccivil_03/leis/l4737.htm",
    "Estatuto da Criança e do Adolescente (Lei nº 8.069/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8069.htm",
    "Estatuto da Pessoa Idosa (Lei nº 10.741/2003)": "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.741.htm",
    "Estatuto da Igualdade Racial (Lei nº 12.288/2010)": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12288.htm",
    "Estatuto da Pessoa com Deficiência (Lei nº 13.146/2015)": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm",
    "Lei Maria da Penha (Lei nº 11.340/2006)": "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm",
    "Lei de Contravenções Penais (Decreto-Lei nº 3.688/41)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm",
    "Lei de Execução Penal (Lei nº 7.210/1984)": "https://www.planalto.gov.br/ccivil_03/leis/l7210.htm",
    "Regime Jurídico dos Servidores Públicos (Lei nº 8.112/1990)": "https://www.planalto.gov.br/ccivil_03/leis/l8112cons.htm",
    "Lei de Licitações e Contratos Administrativos (Lei nº 14.133/2021)": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
}

if "logs" not in st.session_state:
    st.session_state["logs"] = [{"timestamp": datetime.now().strftime("%H:%M:%S"), "texto": "Consola de auditoria inicializada.", "tipo": "Info"}]

def registar_log(texto, tipo):
    hora_atual = datetime.now().strftime("%H:%M:%S")
    st.session_state["logs"].insert(0, {"timestamp": hora_atual, "texto": texto, "tipo": tipo})

st.markdown("<h1 style='text-align: center; color: #1E293B;'>⚖️ Inteligência Documental em Lote - VADE ATUALIZADO</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: #64748B; font-size: 16px;'>Desenvolvido por: Marianne Ramos Ferreira</h2>", unsafe_allow_html=True)
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
    st.subheader("⚙️ Modo de Compilação")

    modo_compilacao = st.radio(
        "Selecione o escopo do documento final:",
        ["📖 Vade Mecum Completo (Texto Integral)", "✂️ Apenas Atualizações (Recortes por Ano)"],
        index=0,
        horizontal=False
    )

    if modo_compilacao == "✂️ Apenas Atualizações (Recortes por Ano)":
        col_anos1, col_anos2 = st.columns([2, 1])
        
        with col_anos1:
            anos_disponiveis = ["2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027"]
            anos_selecionados = st.multiselect(
                "Anos a destacar:",
                options=anos_disponiveis,
                default=["2024", "2025", "2026"]
            )
            
        with col_anos2:
            anos_extras_texto = st.text_input(
                "Outros anos:",
                placeholder="Ex: 2018"
            )

        anos_finais = list(anos_selecionados)
        if anos_extras_texto.strip():
            anos_extras = re.findall(r'\b\d{4}\b', anos_extras_texto)
            anos_finais.extend(anos_extras)

        anos_finais = sorted(list(set(anos_finais)), key=str)
        
        if not anos_finais:
            st.warning("⚠️ Selecione pelo menos um ano para aplicar o recorte de atualizações.")
        else:
            st.info(f"✂️ **Modo Atualizações:** O documento conterá apenas artigos alterados em: **{', '.join(anos_finais)}**")
    else:
        anos_finais = ["VADE COMPLETO"]
        st.success("📖 **Modo Vade Mecum Completo:** O documento conterá TODOS os artigos e a estrutura na íntegra, sem cortes por ano.")

    st.markdown("---")

    if st.button("🚀 Iniciar Coleta e Compilação Automática", use_container_width=True):
        if not anos_finais:
            st.warning("⚠️ Selecione ao menos um ano ou mude para o modo Vade Mecum Completo.")
        elif not lista_final_leis:
            st.warning("⚠️ Nenhuma fonte de dados foi selecionada.")
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
                    
                    if "constituicao" in url_higienizada.lower() or "constituição" in nome_lei.lower():
                        registar_log("🚀 Executando minerador avançado para a Constituição.", "Info")
                        texto_extraido = baixar_constituicao_completa()
                    else:
                        texto_extraido = formatador.raspar_portal_planalto(url_higienizada)
                    
                    if texto_extraido.startswith("Erro"):
                        st.error(f"Falha na extração de: {nome_lei}. Detalhe: {texto_extraido}")
                        registar_log(f"Erro em {nome_lei}: {texto_extraido}", "Erro")
                    else:
                        registar_log(f"Conteúdo de {nome_lei} armazenado com sucesso.", "Sucesso")
                        fila_compilacao.append((nome_lei, texto_extraido))
                    
                    barra_progresso.progress((i + 1) / total_itens)
                    time.sleep(1.0)
                    
                status_coleta.empty()
                barra_progresso.empty()
            else:
                fila_compilacao = lista_final_leis

            if fila_compilacao:
                with st.spinner("⚙️ Gerando relatórios PDF (LaTeX) e Planilha Excel..."):
                    registar_log(f"Iniciando montagem do lote com {len(fila_compilacao)} itens.", "Info")
                    
                    status_pdf, res_pdf = formatador.compilar_pdf(
                        fila_compilacao, 
                        nome_base="VadeMecum_Minerado", 
                        anos_destaque=anos_finais
                    )
                    
                    status_xls, res_xls = formatador.gerar_excel(
                        fila_compilacao,
                        nome_base="VadeMecum_Minerado",
                        anos_destaque=anos_finais
                    )
                    
                    if status_pdf == "sucesso":
                        st.success("🎉 Compilação concluída com sucesso!")
                        registar_log("Documento PDF gerado.", "Sucesso")
                        st.session_state["pdf_pronto"] = res_pdf
                    else:
                        st.error("🚨 Falha na compilação do PDF.")
                        registar_log("Erro no processo de compilação do LaTeX.", "Erro")
                        st.text_area("Log Técnico de Erros:", value=res_pdf, height=200)

                    if status_xls == "sucesso":
                        registar_log("Planilha Excel gerada com sucesso.", "Sucesso")
                        st.session_state["excel_pronto"] = res_xls
            else:
                st.error("Nenhum texto válido foi coletado para compilação.")

with col_direita:
    st.subheader("📄 Painel de Resultados e Downloads")
    
    if "pdf_pronto" in st.session_state and os.path.exists(st.session_state["pdf_pronto"]):
        caminho_pdf = st.session_state["pdf_pronto"]
        with open(caminho_pdf, "rb") as f_pdf:
            dados_pdf = f_pdf.read()
            st.download_button(
                label="📥 Descarregar Vade Mecum Compilado (PDF)",
                data=dados_pdf,
                file_name="VadeMecum_Compilado.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    if "excel_pronto" in st.session_state and os.path.exists(st.session_state["excel_pronto"]):
        caminho_xls = st.session_state["excel_pronto"]
        with open(caminho_xls, "rb") as f_xls:
            dados_xls = f_xls.read()
            st.download_button(
                label="📊 Descarregar Planilha de Dispositivos (Excel .xlsx)",
                data=dados_xls,
                file_name="VadeMecum_Dispositivos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    if "pdf_pronto" in st.session_state and os.path.exists(st.session_state["pdf_pronto"]):
        base64_pdf = base64.b64encode(dados_pdf).decode('utf-8')
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
                document.write('<p style="font-family:sans-serif; color:#64748B; font-size:14px;">Utilize os botões acima para transferir os ficheiros.</p>');
            }}
        </script>
        """
        st.components.v1.html(html_preview, height=600)
