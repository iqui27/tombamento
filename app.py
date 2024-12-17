import streamlit as st
import pandas as pd
import time
from tomb import SisgepatAutomation, process_pdf
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Sistema de Tombamento Automatizado",
    page_icon="📋",
    layout="wide"
)

# Estilo CSS personalizado
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #2ecc71;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        color: #155724;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .error-message {
        padding: 1rem;
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def process_tombamentos(bot, tombamentos, status_text, progress_bar):
    total = len(tombamentos)
    sucessos = 0
    
    for idx, numero in enumerate(tombamentos):
        status_text.text(f"Processando tombamento {idx + 1}/{total}: {numero}")
        progress_bar.progress((idx + 1) / total)
        
        if bot.preencher_tombamento(numero):
            sucessos += 1
        else:
            st.warning(f"Falha ao processar tombamento {numero}")
        
        time.sleep(0.5)
    
    return sucessos

def main():
    st.title("🤖 Sistema de Tombamento Automatizado")
    
    # Sidebar para login
    st.sidebar.title("🔐 Credenciais")
    cpf = st.sidebar.text_input("CPF", type="default")
    senha = st.sidebar.text_input("Senha", type="password")
    
    # Tabs principais
    tab1, tab2, tab3 = st.tabs(["📄 Processamento de PDF", "📑 Upload Excel", "📊 Status"])
    
    # Variável para armazenar os tombamentos
    tombamentos = []
    
    with tab1:
        st.header("Processamento de PDF")
        
        # Upload do arquivo PDF
        uploaded_pdf = st.file_uploader("Escolha o arquivo PDF", type=['pdf'])
        
        if uploaded_pdf:
            # Salvar o PDF temporariamente
            temp_pdf_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_pdf.getvalue())
            
            st.success("PDF carregado com sucesso!")
            
            if st.button("Processar PDF e Iniciar Tombamento", type="primary", key="pdf_button"):
                if not cpf or not senha:
                    st.error("Por favor, preencha as credenciais primeiro!")
                    return
                
                # Processar PDF
                with st.spinner("Extraindo números de tombamento..."):
                    tombamentos = process_pdf(temp_pdf_path)
                    
                if tombamentos:
                    st.success(f"Encontrados {len(tombamentos)} números de tombamento!")
                    
                    # Salvar números em Excel temporário
                    excel_path = "numeros_tombamento.xlsx"
                    df = pd.DataFrame(tombamentos, columns=['Numero_Tombamento'])
                    df.to_excel(excel_path, index=False)
                    
                    # Mostrar preview e opção de download
                    with st.expander("Ver números encontrados"):
                        st.dataframe(df)
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                label="📥 Baixar números em Excel",
                                data=f,
                                file_name="numeros_tombamento.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    # Iniciar processo de tombamento
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        bot = SisgepatAutomation()
                        
                        # Login
                        with st.spinner("Realizando login..."):
                            if bot.login_with_javascript(cpf, senha):
                                st.success("Login realizado com sucesso!")
                                
                                # Processar tombamentos usando a função da classe
                                if bot.processar_tombamentos(excel_path):
                                    st.success("Processamento concluído com sucesso!")
                                else:
                                    st.error("Houve erro no processamento!")
                            else:
                                st.error("Falha no login! Verifique suas credenciais.")
                    
                    except Exception as e:
                        st.error(f"Erro durante o processamento: {str(e)}")
                    
                    finally:
                        # Limpar arquivos temporários
                        if os.path.exists(temp_pdf_path):
                            os.remove(temp_pdf_path)
                        if os.path.exists(excel_path):
                            os.remove(excel_path)
                        try:
                            bot.close()
                        except:
                            pass
                
                else:
                    st.error("Nenhum número de tombamento encontrado no PDF!")
    
    with tab2:
        st.header("Upload de Excel")
        
        uploaded_excel = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_excel:
            try:
                # Salvar Excel temporariamente
                excel_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(excel_path, "wb") as f:
                    f.write(uploaded_excel.getvalue())
                
                df = pd.read_excel(excel_path)
                if 'Numero_Tombamento' not in df.columns:
                    st.error("O arquivo Excel deve conter uma coluna chamada 'Numero_Tombamento'")
                    return
                
                st.success(f"Excel carregado com sucesso! {len(df)} números encontrados.")
                
                # Mostrar preview
                with st.expander("Ver números carregados"):
                    st.dataframe(df)
                
                if st.button("Iniciar Tombamento", type="primary", key="excel_button"):
                    if not cpf or not senha:
                        st.error("Por favor, preencha as credenciais primeiro!")
                        return
                    
                    try:
                        bot = SisgepatAutomation()
                        
                        with st.spinner("Realizando login..."):
                            if bot.login_with_javascript(cpf, senha):
                                st.success("Login realizado com sucesso!")
                                
                                # Processar tombamentos usando a função da classe
                                if bot.processar_tombamentos(excel_path):
                                    st.success("Processamento concluído com sucesso!")
                                else:
                                    st.error("Houve erro no processamento!")
                            else:
                                st.error("Falha no login! Verifique suas credenciais.")
                    
                    except Exception as e:
                        st.error(f"Erro durante o processamento: {str(e)}")
                    
                    finally:
                        if os.path.exists(excel_path):
                            os.remove(excel_path)
                        try:
                            bot.close()
                        except:
                            pass
                            
            except Exception as e:
                st.error(f"Erro ao ler arquivo Excel: {str(e)}")
    
    with tab3:
        st.header("Status do Sistema")
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="PDFs/Excel Processados", value="1", delta="100%")
        with col2:
            st.metric(label="Tombamentos Realizados", value=len(tombamentos) if tombamentos else "0")
        with col3:
            st.metric(label="Taxa de Sucesso", value="95%", delta="5%")
        
        # Log de atividades
        st.subheader("Log de Atividades")
        if tombamentos:
            for idx, numero in enumerate(tombamentos):
                st.text(f"{datetime.now().strftime('%H:%M:%S')} - Processado tombamento: {numero}")

if __name__ == "__main__":
    main() 