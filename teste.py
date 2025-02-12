import streamlit as st
from tomb import SisgepatAutomation, process_pdf
import pandas as pd
import time

st.set_page_config(page_title="Teste de Funções", layout="wide")

def load_credentials():
    if 'cpf' in st.session_state and 'senha' in st.session_state:
        return st.session_state.cpf, st.session_state.senha
    return None, None

def save_credentials(cpf, senha):
    st.session_state.cpf = cpf
    st.session_state.senha = senha



def test_login():
    st.subheader("Teste de Login")
    
    cpf = st.text_input("CPF")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Testar Login"):
        try:
            bot = SisgepatAutomation()
            with st.spinner("Tentando login..."):
                if bot.login_with_javascript(cpf, senha):
                    st.success("✅ Login realizado com sucesso!")
                else:
                    st.error("❌ Falha no login")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
        finally:
            bot.close()

def test_navegacao():
    st.subheader("Teste de Navegação")
    
    cpf = st.text_input("CPF", key="nav_cpf")
    senha = st.text_input("Senha", type="password", key="nav_senha")
    
    col1, col2 = st.columns(2)
    with col1:
        test_dados_gerais = st.button("Testar Navegação para Dados Gerais")
    with col2:
        numero_tgcd = st.text_input("Número TGCD")
        test_edicao = st.button("Testar Navegação para Edição")
    
    if test_dados_gerais or (test_edicao and numero_tgcd):
        try:
            bot = SisgepatAutomation()
            with st.spinner("Realizando login..."):
                if bot.login_with_javascript(cpf, senha):
                    st.success("✅ Login realizado com sucesso!")
                    
                    with st.spinner("Navegando..."):
                        if test_dados_gerais:
                            if bot.navegar_para_dados_gerais():
                                st.success("✅ Navegação para Dados Gerais realizada com sucesso!")
                            else:
                                st.error("❌ Falha na navegação para Dados Gerais")
                        elif test_edicao:
                            if bot.navegar_para_edicao_tgcd(numero_tgcd):
                                st.success("✅ Navegação para Edição realizada com sucesso!")
                            else:
                                st.error("❌ Falha na navegação para Edição")
                else:
                    st.error("❌ Falha no login")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
        finally:
            bot.close()

def test_preencher_tombamento():
    st.subheader("Teste de Preenchimento de Tombamento")
    
    cpf = st.text_input("CPF", key="tomb_cpf")
    senha = st.text_input("Senha", type="password", key="tomb_senha")
    numero = st.text_input("Número do Tombamento")
    
    col1, col2 = st.columns(2)
    with col1:
        modo_novo = st.button("Testar Novo Tombamento")
    with col2:
        numero_tgcd = st.text_input("Número TGCD (para edição)")
        modo_edicao = st.button("Testar Edição de Tombamento")
    
    if modo_novo or (modo_edicao and numero_tgcd):
        try:
            bot = SisgepatAutomation()
            with st.spinner("Realizando login..."):
                if bot.login_with_javascript(cpf, senha):
                    st.success("✅ Login realizado com sucesso!")
                    
                    with st.spinner("Navegando..."):
                        if modo_novo:
                            if bot.navegar_para_dados_gerais():
                                st.success("✅ Navegação realizada com sucesso!")
                        else:
                            if bot.navegar_para_edicao_tgcd(numero_tgcd):
                                st.success("✅ Navegação realizada com sucesso!")
                        
                        # Tenta preencher o tombamento
                        with st.spinner(f"Preenchendo tombamento {numero}..."):
                            if bot.preencher_tombamento(numero):
                                st.success(f"✅ Tombamento {numero} preenchido com sucesso!")
                            else:
                                st.error(f"❌ Falha ao preencher tombamento {numero}")
                else:
                    st.error("❌ Falha no login")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
        finally:
            bot.close()

def test_pdf():
    st.subheader("Teste de Processamento de PDF")
    
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")
    
    if uploaded_file and st.button("Processar PDF"):
        with st.spinner("Processando PDF..."):
            # Salva o arquivo temporariamente
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Processa o PDF
            tombamentos = process_pdf("temp.pdf")
            
            if tombamentos:
                st.success(f"✅ Encontrados {len(tombamentos)} números de tombamento!")
                st.write("Números encontrados:")
                df = pd.DataFrame(tombamentos, columns=['Numero_Tombamento'])
                st.dataframe(df)
            else:
                st.error("❌ Nenhum número de tombamento encontrado!")

def test_processar_lotes():
    st.subheader("Teste de Processamento em Lotes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cpf = st.text_input("CPF", key="lote_cpf")
        senha = st.text_input("Senha", type="password", key="lote_senha")
        uploaded_file = st.file_uploader("Arquivo Excel com tombamentos", type=["xlsx", "xls"])
        
    with col2:
        tamanho_lote = st.number_input("Tamanho do Lote", min_value=1, value=100)
        numero_tgcd = st.text_input("Número TGCD (opcional)", key="lote_tgcd")
        
    if uploaded_file and st.button("Iniciar Processamento em Lotes"):
        try:
            # Salva o arquivo temporariamente
            with open("temp.xlsx", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            bot = SisgepatAutomation()
            stop_button = st.button("🛑 Parar Processamento")
            
            with st.spinner("Realizando login..."):
                if bot.login_with_javascript(cpf, senha):
                    st.success("✅ Login realizado com sucesso!")
                    
                    # Containers para status
                    status_container = st.empty()
                    progress_container = st.empty()
                    info_container = st.empty()
                    
                    try:
                        for resultado in bot.processar_tombamentos_em_lotes(
                            "temp.xlsx", 
                            tamanho_lote=tamanho_lote,
                            numero_tgcd=numero_tgcd if numero_tgcd else None
                        ):
                            if stop_button:
                                bot.stop_processing()
                                st.warning("⚠️ Parando processamento...")
                            
                            if resultado['status'] == 'processando':
                                # Atualiza status
                                status_container.text(
                                    f"Processando lote {resultado['lote_atual']}/{resultado['total_lotes']}"
                                )
                                
                                # Atualiza barra de progresso
                                progress_container.progress(resultado['progresso_lote'])
                                
                                # Atualiza informações
                                info_container.text(
                                    f"Tombamento atual: {resultado['numero']}\n"
                                    f"Sucessos no lote: {resultado['sucessos_lote']}/{resultado['total_lote']}"
                                )
                                
                            elif resultado['status'] == 'lote_concluido':
                                st.success(f"✅ {resultado['mensagem']}")
                                time.sleep(1)
                                
                            elif resultado['status'] == 'erro':
                                st.error(f"❌ {resultado['mensagem']}")
                                
                            elif resultado['status'] == 'processo_finalizado':
                                st.success(f"🎉 {resultado['mensagem']}")
                                
                    except Exception as e:
                        st.error(f"❌ Erro durante processamento: {str(e)}")
                        
                else:
                    st.error("❌ Falha no login")
                    
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            
        finally:
            if 'bot' in locals():
                bot.close()

def main():
    st.title("🔧 Página de Testes")
    
    tabs = st.tabs([
        "🔐 Teste Login",
        "🧭 Teste Navegação",
        "📝 Teste Tombamento",
        "📄 Teste PDF",
        "🔄 Teste Lotes"  # Nova aba
    ])
    
    with tabs[0]:
        test_login()
    
    with tabs[1]:
        test_navegacao()
    
    with tabs[2]:
        test_preencher_tombamento()
    
    with tabs[3]:
        test_pdf()
        
    with tabs[4]:
        test_processar_lotes()

if __name__ == "__main__":
    main()