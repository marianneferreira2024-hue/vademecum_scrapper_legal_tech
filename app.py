import streamlit as st

import os

import base64

from datetime import datetime

import formatador

import re



st.set_page_config(page_title="LAPEJURI - LegalTech", page_icon="⚖️", layout="wide")



MAPA_LEIS = {

    "Código Penal (Decreto-Lei nº 2.848/40)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",

    "Código de Processo Penal (Decreto-Lei nº 3.689/41)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689.htm",

    "Lei de Crimes Hediondos (Lei nº 8.072/90)": "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm",

    "Lei de Introdução às Normas do Direito Brasileiro (LINDB)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm"

}



if "logs" not in st.session_state:

    st.session_state["logs"] = [{"timestamp": datetime.now().strftime("%H:%M:%S"), "texto": "Consola de auditoria inicializada.", "tipo": "Info"}]



def registar_log(texto, tipo):

    hora_atual = datetime.now().strftime("%H:%M:%S")

    st.session_state["logs"].insert(0, {"timestamp": hora_atual, "texto": texto, "tipo": tipo})



st.markdown("<h1 style='text-align: center; color: #1E293B;'>⚖️ Inteligência Documental - LAPEJURI</h1>", unsafe_allow_html=True)

st.divider()



col_esquerda, col_direita = st.columns([1, 1])



with col_esquerda:

    st.subheader("📥 Configuração da Coleta")

    

    fonte_opcao = st.radio(

        "Como deseja inserir a legislação?", 

        ["Capturar do Portal Planalto (Web Scraper)", "Colar Texto Bruto Manuscrito"],

        horizontal=False

    )

    

    url_final_scraping = ""

    texto_entrada = ""

    

    if fonte_opcao == "Capturar do Portal Planalto (Web Scraper)":

        opcao_lei = st.selectbox("Selecione um Diploma Cadastrado:", list(MAPA_LEIS.keys()) + ["Outro (Digitar link personalizado)"])

        if opcao_lei == "Outro (Digitar link personalizado)":

            url_final_scraping = st.text_input("Cole a URL do documento compilado do Planalto:", placeholder="https://www.planalto.gov.br/...")

        else:

            url_final_scraping = MAPA_LEIS[opcao_lei]

            st.info(f"🔗 Link mapeado: `{url_final_scraping}`")

            

    elif fonte_opcao == "Colar Texto Bruto Manuscrito":

        texto_entrada = st.text_area("Cole os artigos do Vade Mecum aqui:", height=200)



    st.markdown("---")

    st.subheader("📅 Filtro de Destaques")

    anos_disponiveis = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]

    anos_selecionados = st.multiselect(

        "Selecione as alterações de quais anos deseja envelopar em caixas cinzas (Notas):",

        options=anos_disponiveis,

        default=[2024, 2025, 2026]

    )



    # Botão perfeitamente alinhado com 4 espaços (dentro do with col_esquerda)

    if st.button("🚀 Iniciar Coleta e Compilação Automática"):

        if not anos_selecionados:

            st.warning("⚠️ Selecione pelo menos um ano para servir de filtro de alterações.")

        else:

            if fonte_opcao == "Capturar do Portal Planalto (Web Scraper)":

                if not url_final_scraping.strip():

                    st.warning("⚠️ Insira uma URL válida do Planalto.")

                else:

                    with st.spinner("🕵️‍♂️ Robô minerando dados do Planalto..."):

                        url_bruta = str(url_final_scraping)

                        extrator = re.search(r'(https?://[^\s\]\)\'"]+)', url_bruta)

                        

                        if extrator:

                            url_higienizada = extrator.group(1)

                        else:

                            url_higienizada = url_bruta.strip().replace('"', '').replace("'", "")

                            url_higienizada = "".join(url_higienizada.split())

                        

                        registar_log(f"Acessando o endereço limpo: {url_higienizada}", "Scraping")

                        texto_entrada = formatador.raspar_portal_planalto(url_higienizada)

                        

                        if texto_entrada.startswith("Erro"):

                            st.error(texto_entrada)

                            registar_log(texto_entrada, "Erro")

                            texto_entrada = ""

                        else:

                            registar_log("Texto extraído com sucesso do Planalto.", "Sucesso")

            

            if texto_entrada.strip():

                with st.spinner("⚙️ Compilando PDF via MiKTeX..."):

                    registar_log(f"Compilando com destaques para os anos: {anos_selecionados}", "Info")

                    status, resultado = formatador.compilar_pdf(

                        texto_entrada, 

                        nome_base="VadeMecum_Minerado", 

                        anos_destaque=anos_selecionados

                    )

                    

                    if status == "sucesso":

                        st.success("🎉 Processo concluído com sucesso!")

                        registar_log("Documento PDF gerado com sucesso.", "Sucesso")

                        st.session_state["pdf_pronto"] = resultado

                    else:

                        st.error("🚨 Falha na compilação estrutural do LaTeX.")

                        registar_log("Erro de compilação ou falta de executável pdflatex.", "Erro")

                        st.text_area("Log Técnico de Erros:", value=resultado, height=200)

            else:

                st.warning("⚠️ Forneça uma string de texto ou execute o scraper com um link válido.")



with col_direita:

    st.subheader("📄 Painel de Resultados")

    

    if "pdf_pronto" in st.session_state and os.path.exists(st.session_state["pdf_pronto"]):

        caminho_pdf = st.session_state["pdf_pronto"]

        

        with open(caminho_pdf, "rb") as f_pdf:

            dados_pdf = f_pdf.read()

            st.download_button(

                label="⬇️ Descarregar Arquivo PDF",

                data=dados_pdf,

                file_name="VadeMecum_LAPEJURI.pdf",

                mime="application/pdf",

                use_container_width=True

            )

        

        base64_pdf = base64.b64encode(dados_pdf).decode('utf-8')

        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="480" style="border:1px solid #64748B; border-radius:8px;"></iframe>'

        st.markdown(pdf_display, unsafe_allow_html=True)

    else:

        st.info("ℹ️ Aguardando processamento. Escolha a lei, ajuste os anos desejados e clique em Iniciar.")



    st.markdown("---")

    st.subheader("📊 Trilha de Auditoria")

    for log in st.session_state["logs"]:

        badge = "🔴" if log["tipo"] == "Erro" else ("🟢" if log["tipo"] == "Sucesso" else "🔵")

        st.markdown(f"<div style='background-color:#1b242e; border-left:4px solid #899ab3; padding:8px; margin-bottom:5px; font-family:monospace; font-size:0.85rem;'><b>[{log['timestamp']}] {badge} {log['tipo']}:</b> {log['texto']}</div>", unsafe_allow_html=True)