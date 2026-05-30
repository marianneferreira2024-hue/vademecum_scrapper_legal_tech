import streamlit as st
import os
import base64
import time
from formatador import compilar_pdf, raspar_portal_planalto

st.set_page_config(page_title="LAPEJURI Cloud", layout="wide", page_icon="⚖️")
st.title("⚖️ Mineração em Lote - Novidades Legislativas (2024-2026)")

# Seu dicionário de leis mapeadas
MAPA_LEIS = {
    "Código Penal (CP)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
    "Código de Processo Penal (CPP)": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689.htm",
    "Lei de Crimes Hediondos": "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm",
    "LINDB": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm",
    "Código Civil (CC)": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
}

if "pdf_pronto" not in st.session_state:
    st.session_state.pdf_pronto = False
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

# 📌 NOVO: Interface de Seleção Múltipla
col1, col2 = st.columns([2, 1])

with col1:
    leis_selecionadas = st.multiselect(
        "📚 Selecione as leis para compor o Vade Mecum (Pode escolher várias):",
        options=list(MAPA_LEIS.keys()),
        default=["Código Penal (CP)", "Código de Processo Penal (CPP)"]
    )
    
    urls_livres = st.text_area(
        "🔗 Ou cole URLs adicionais do Planalto (Uma por linha):",
        placeholder="https://www.planalto.gov.br/..."
    )

with col2:
    anos = st.multiselect("Filtrar estritamente por:", ["2024", "2025", "2026"], default=["2024", "2025", "2026"])

if st.button("🚀 Iniciar Mineração em Série e Compilar PDF", use_container_width=True):
    
    # 1. Montar a lista final de links para processar
    lista_para_minerar = []
    for lei in leis_selecionadas:
        lista_para_minerar.append((lei, MAPA_LEIS[lei]))
        
    for i, url in enumerate(urls_livres.split('\n')):
        url = url.strip()
        if url:
            lista_para_minerar.append((f"Legislação Adicional {i+1}", url))

    if not lista_para_minerar:
        st.error("Selecione pelo menos uma lei ou insira uma URL válida.")
    else:
        st.session_state.pdf_pronto = False
        st.session_state.pdf_bytes = None
        
        lista_textos_extraidos = []
        
        # 2. Loop de Raspagem com Barra de Progresso
        barra_progresso = st.progress(0)
        status_texto = st.empty()
        
        total_leis = len(lista_para_minerar)
        
        for indice, (nome_lei, url_lei) in enumerate(lista_para_minerar):
            status_texto.markdown(f"**Raspando {indice + 1}/{total_leis}:** {nome_lei}...")
            
            texto_bruto = raspar_portal_planalto(url_lei)
            if texto_bruto.startswith("Erro"):
                st.warning(f"⚠️ Falha ao ler {nome_lei}: {texto_bruto}")
            else:
                lista_textos_extraidos.append((nome_lei, texto_bruto))
                
            # Atualiza barra
            barra_progresso.progress((indice + 1) / total_leis)
            time.sleep(0.5) # Evita sobrecarga de requests no Planalto
            
        status_texto.empty()
        
        # 3. Compilação Unificada no LaTeX
        if not lista_textos_extraidos:
            st.error("Nenhum texto foi extraído com sucesso.")
        else:
            with st.spinner("Compilando PDF unificado de duas colunas... (Isso pode levar alguns segundos)"):
                status, resultado = compilar_pdf(lista_textos_extraidos, nome_base="VadeMecum_Minerado", anos_destaque=anos)
            
            if status == "sucesso" and os.path.exists(resultado):
                with open(resultado, "rb") as f:
                    st.session_state.pdf_bytes = f.read()
                st.session_state.pdf_pronto = True
                st.success(f"🎉 PDF Gerado com sucesso! Contendo {len(lista_textos_extraidos)} leis compiladas juntas.")
            else:
                st.error("Erro técnico ao compilar o arquivo LaTeX.")
                with st.expander("Ver Log do Servidor:"):
                    st.code(resultado)

# Renderiza Resultados
if st.session_state.pdf_pronto and st.session_state.pdf_bytes is not None:
    st.markdown("---")
    st.download_button(
        label="📥 Baixar Vade Mecum Multi-Leis (PDF)",
        data=st.session_state.pdf_bytes,
        file_name="VadeMecum_LAPEJURI_Lote.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" style="border:1px solid #64748B; border-radius:8px;"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)