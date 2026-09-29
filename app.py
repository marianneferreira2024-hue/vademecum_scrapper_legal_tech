import streamlit as st
import os
import time
from formatador import (
    raspar_portal_planalto, 
    processar_texto_para_dataframe, 
    gerar_buffer_excel, 
    compilar_pdf
)

st.set_page_config(page_title="LAPEJURI Extrator v5", layout="wide")
st.title("⚖️ Extrator de Legislação: Excel (Homepage) & PDF (LaTeX)")

# Configurações iniciais de sessão
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None
if "df_excel" not in st.session_state: st.session_state.df_excel = None

# Painel de Entrada
col_url, col_nome = st.columns([2, 1])
with col_url:
    url_alvo = st.text_input("URL do Planalto:", placeholder="Ex: https://www.planalto.gov.br/ccivil_03/codigo_penal.htm")
with col_nome:
    diploma_legal = st.text_input("Diploma Legal (Para o Excel):", value="Código Penal")

col_escopo, col_anos = st.columns([1, 1])
with col_escopo:
    escopo = st.radio("Filtro de Conteúdo:", ["Código / Lei Completo(a)", "Apenas Alterações Recentes (2024-2026)"])
with col_anos:
    anos = st.multiselect("Anos para destaque recente:", ["2024", "2025", "2026"], default=["2024", "2025", "2026"])

st.markdown("---")

# Botões de Execução
btn_col1, btn_col2 = st.columns([1, 1])

with btn_col1:
    executar_excel = st.button("📊 Extrair para Excel (.xlsx)")

with btn_col2:
    executar_pdf = st.button("🚀 Compilar PDF em 2 Colunas (LaTeX)")

apenas_recentes = (escopo == "Apenas Alterações Recentes (2024-2026)")

# AÇÃO 1: EXCEL
if executar_excel:
    if not url_alvo:
        st.error("Cole uma URL válida do Planalto.")
    else:
        with st.spinner("1/2: Minerando dados brutos do Planalto..."):
            texto_bruto = raspar_portal_planalto(url_alvo)
            
        if texto_bruto.startswith("Erro"):
            st.error(texto_bruto)
        else:
            with st.spinner("2/2: Montando a estrutura em tabela (DIPLOMA | DISPOSITIVO | TEXTO)..."):
                st.session_state.df_excel = processar_texto_para_dataframe(
                    texto_bruto=texto_bruto,
                    diploma_legal=diploma_legal,
                    apenas_recentes=apenas_recentes,
                    anos_destaque=anos
                )
            st.success(f"🎉 Extração para Excel concluída! {len(st.session_state.df_excel)} dispositivos processados.")

# AÇÃO 2: PDF
if executar_pdf:
    if not url_alvo:
        st.error("Cole uma URL válida do Planalto.")
    else:
        diretorio = os.path.dirname(os.path.abspath(__file__))
        pdf_antigo = os.path.join(diretorio, "VadeMecum_Minerado.pdf")
        if os.path.exists(pdf_antigo):
            try: os.remove(pdf_antigo)
            except: pass
            
        with st.spinner("1/2: Minerando dados brutos do Planalto..."):
            texto_bruto = raspar_portal_planalto(url_alvo)
            
        if texto_bruto.startswith("Erro"):
            st.error(texto_bruto)
        else:
            with st.spinner("2/2: Gerando arquivo LaTeX e compilando PDF em 2 colunas..."):
                status, resultado = compilar_pdf(texto_bruto, nome_base="VadeMecum_Minerado", anos_destaque=anos)
            
            if status == "sucesso" and os.path.exists(resultado):
                time.sleep(0.5)
                with open(resultado, "rb") as f:
                    st.session_state.pdf_bytes = f.read()
                st.success("🎉 Compilação do PDF concluída com sucesso!")
            else:
                st.error("Falha na compilação do LaTeX.")
                with st.expander("🔍 Log de erros do LaTeX:"):
                    st.code(resultado, language="text")

# EXIBIÇÃO DOS RESULTADOS

# Área de Download/Prévia do EXCEL
if st.session_state.df_excel is not None and not st.session_state.df_excel.empty:
    st.subheader("📊 Acervo Processado para Excel")
    st.dataframe(st.session_state.df_excel, use_container_width=True, height=300)
    
    excel_buffer = gerar_buffer_excel(st.session_state.df_excel)
    st.download_button(
        label="📥 Baixar Tabela Excel (.xlsx)",
        data=excel_buffer,
        file_name=f"{diploma_legal.replace(' ', '_')}_Base_Planalto.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Área de Download do PDF
if st.session_state.pdf_bytes is not None:
    st.subheader("📄 PDF Compilado em Duas Colunas")
    st.download_button(
        label="📥 Baixar Vade Mecum em PDF",
        data=st.session_state.pdf_bytes,
        file_name="VadeMecum_Novidades.pdf",
        mime="application/pdf"
    )