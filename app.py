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

def process_multiple_pdfs(pdf_files):
    """
    Processa múltiplos arquivos PDF e retorna um DataFrame combinado
    """
    all_tombamentos = []
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    for idx, pdf_file in enumerate(pdf_files):
        # Salvar PDF temporariamente
        temp_pdf_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_file.getvalue())
        
        progress_text.text(f"Processando PDF {idx + 1}/{len(pdf_files)}: {pdf_file.name}")
        progress_bar.progress((idx + 1) / len(pdf_files))
        
        try:
            # Processar PDF
            tombamentos = process_pdf(temp_pdf_path)
            if tombamentos:
                all_tombamentos.extend(tombamentos)
            
            # Limpar arquivo temporário
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                
        except Exception as e:
            st.error(f"Erro ao processar {pdf_file.name}: {str(e)}")
    
    # Remover duplicatas mantendo a ordem
    unique_tombamentos = list(dict.fromkeys(all_tombamentos))
    
    return pd.DataFrame(unique_tombamentos, columns=['Numero_Tombamento'])

def main():
    st.title("🤖 Sistema de Tombamento Automatizado")
    
    # Sidebar para login
    st.sidebar.title("🔐 Credenciais")
    cpf = st.sidebar.text_input("CPF", type="default")
    senha = st.sidebar.text_input("Senha", type="password")
    
    # Tabs principais
    tab1, tab2, tab3 = st.tabs(["📄 Processamento de PDF", "📑 Upload Excel", "📊 Status"])
    
    with tab1:
        st.header("Processamento de PDF")
        
        # Upload de múltiplos arquivos PDF
        uploaded_pdfs = st.file_uploader(
            "Escolha os arquivos PDF", 
            type=['pdf'], 
            accept_multiple_files=True
        )
        
        if uploaded_pdfs:
            total_pdfs = len(uploaded_pdfs)
            st.success(f"{total_pdfs} {'arquivo' if total_pdfs == 1 else 'arquivos'} carregado{'s' if total_pdfs > 1 else ''}!")
            
            if st.button("Processar PDFs e Iniciar Tombamento", type="primary", key="pdf_button"):
                if not cpf or not senha:
                    st.error("Por favor, preencha as credenciais primeiro!")
                    return
                
                # Processar PDFs
                with st.spinner("Extraindo números de tombamento..."):
                    df = process_multiple_pdfs(uploaded_pdfs)
                    
                if not df.empty:
                    st.success(f"Encontrados {len(df)} números de tombamento únicos!")
                    
                    # Salvar números em Excel temporário
                    excel_path = "numeros_tombamento_combinados.xlsx"
                    df.to_excel(excel_path, index=False)
                    
                    # Mostrar preview e opção de download
                    with st.expander("Ver números encontrados"):
                        st.dataframe(df)
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                label="📥 Baixar números em Excel",
                                data=f,
                                file_name="numeros_tombamento_combinados.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    try:
                        bot = SisgepatAutomation()
                        
                        # Login
                        with st.spinner("Realizando login..."):
                            if bot.login_with_javascript(cpf, senha):
                                st.success("Login realizado com sucesso!")
                                
                                # Componentes de progresso
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                metrics_cols = st.columns(3)
                                tempo_col = metrics_cols[0].empty()
                                progresso_col = metrics_cols[1].empty()
                                sucessos_col = metrics_cols[2].empty()
                                
                                # Processar tombamentos
                                for info in bot.processar_tombamentos(excel_path):
                                    if info['status'] == 'inicio':
                                        status_text.text("Iniciando processamento...")
                                        tempo_col.metric("Tempo Estimado", f"{info['tempo_estimado']//60} min")
                                        
                                    elif info['status'] == 'processando':
                                        # Atualiza barra de progresso
                                        progress_bar.progress(info['progresso'])
                                        
                                        # Atualiza status
                                        status_text.text(f"Processando {info['index']}/{info['total']}: {info['numero']}")
                                        
                                        # Atualiza métricas
                                        tempo_col.metric("Tempo Restante", f"{info['tempo_restante']//60:.0f} min")
                                        progresso_col.metric("Progresso", f"{info['progresso']*100:.1f}%")
                                        
                                    elif info['status'] == 'finalizando':
                                        status_text.text("Finalizando processamento...")
                                        
                                    elif info['status'] == 'concluido':
                                        progress_bar.progress(1.0)
                                        status_text.text("Processamento concluído!")
                                        tempo_col.metric("Tempo Total", f"{info['tempo_total']//60:.0f} min")
                                        sucessos_col.metric("Sucessos", f"{info['sucessos']}/{info['total']}")
                                        st.success("Processamento concluído com sucesso!")
                                        
                                    elif info['status'] == 'erro':
                                        st.error(f"Erro no processamento: {info['mensagem']}")
                                        break
                            else:
                                st.error("Falha no login! Verifique suas credenciais.")
                    
                    except Exception as e:
                        st.error(f"Erro durante o processamento: {str(e)}")
                    
                    finally:
                        # Limpar arquivo temporário
                        if os.path.exists(excel_path):
                            os.remove(excel_path)
                        try:
                            bot.close()
                        except:
                            pass
                
                else:
                    st.error("Nenhum número de tombamento encontrado nos PDFs!")
                
                # Após processar PDFs:
                st.session_state.pdfs_processados += len(uploaded_pdfs)
                st.session_state.tombamentos_realizados += len(df)
                st.session_state.log_atividades.append(
                    f"{datetime.now().strftime('%H:%M:%S')} - Processados {len(df)} números de {len(uploaded_pdfs)} PDFs"
                )
    
    with tab2:
        st.header("Upload de Excel")
        
        uploaded_excel = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_excel:
            try:
                df = pd.read_excel(uploaded_excel)
                if 'Numero_Tombamento' not in df.columns:
                    st.error("O arquivo Excel deve conter uma coluna chamada 'Numero_Tombamento'")
                    return
                
                st.success(f"Excel carregado com sucesso! {len(df)} números encontrados.")
                
                # Carrega histórico de processamento se existir
                historico_file = 'historico_tombamento.xlsx'
                if os.path.exists(historico_file):
                    df_historico = pd.read_excel(historico_file)
                    sucessos = df_historico[df_historico['sucesso']]['numero'].tolist()
                    falhas = df_historico[~df_historico['sucesso']]['numero'].tolist()
                    
                    # Mostra estatísticas do histórico
                    with st.expander("📊 Ver histórico de processamento"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Processados com sucesso", len(sucessos))
                        with col2:
                            st.metric("Falhas", len(falhas))
                        with col3:
                            taxa = len(sucessos)/(len(sucessos) + len(falhas)) * 100 if sucessos or falhas else 0
                            st.metric("Taxa de Sucesso", f"{taxa:.1f}%")
                        
                        # Tabs para ver detalhes
                        tab_sucesso, tab_falha = st.tabs(["✅ Sucessos", "❌ Falhas"])
                        with tab_sucesso:
                            if sucessos:
                                st.dataframe(df_historico[df_historico['sucesso']])
                            else:
                                st.info("Nenhum tombamento processado com sucesso ainda.")
                        
                        with tab_falha:
                            if falhas:
                                st.dataframe(df_historico[~df_historico['sucesso']])
                            else:
                                st.success("Nenhuma falha registrada!")
                
                # Opções de processamento
                opcao = st.radio(
                    "Selecione o modo de processamento:",
                    ["✨ Processar todos",
                     "🎯 Processar selecionados",
                     "🔄 Reprocessar falhas",
                     "📝 Processar pendentes"]
                )
                
                if opcao == "🎯 Processar selecionados":
                    # Permite selecionar números específicos
                    st.write("Selecione os números para processar:")
                    
                    # Agrupa checkboxes em colunas para melhor visualização
                    cols = st.columns(4)
                    selected_indices = []
                    
                    for idx, row in df.iterrows():
                        numero = row['Numero_Tombamento']
                        col_idx = idx % 4
                        if cols[col_idx].checkbox(
                            f"{numero}",
                            key=f"check_{idx}",
                            help="Marque para processar este número"
                        ):
                            selected_indices.append(idx)
                    
                    if not selected_indices:
                        st.warning("⚠️ Selecione pelo menos um número para processar")
                        return
                
                elif opcao == "🔄 Reprocessar falhas":
                    if not os.path.exists(historico_file):
                        st.warning("⚠️ Não há histórico de processamentos anteriores")
                        return
                    
                    # Filtra apenas os números que falharam
                    df_temp = df[df['Numero_Tombamento'].isin(falhas)]
                    if df_temp.empty:
                        st.success("✨ Não há falhas para reprocessar!")
                        return
                    df = df_temp
                
                elif opcao == "📝 Processar pendentes":
                    if os.path.exists(historico_file):
                        # Filtra números que nunca foram processados
                        processados = df_historico['numero'].tolist()
                        df_temp = df[~df['Numero_Tombamento'].isin(processados)]
                        if df_temp.empty:
                            st.success("✨ Não há números pendentes para processar!")
                            return
                        df = df_temp
                
                # Mostra preview dos números selecionados
                with st.expander("🔍 Ver números a processar"):
                    st.dataframe(df)
                    st.info(f"Total de números a processar: {len(df)}")
                
                # Botão de processamento
                col1, col2 = st.columns([3, 1])
                with col1:
                    iniciar = st.button(
                        "▶️ Iniciar Processamento", 
                        type="primary",
                        help="Clique para iniciar o processamento dos números selecionados"
                    )
                with col2:
                    tempo_estimado = len(df) * 10  # 10 segundos por tombamento
                    st.info(f"⏱️ Tempo estimado: {tempo_estimado//60} min")
                
                if iniciar:
                    # ... resto do código de processamento ...
                    
                    try:
                        bot = SisgepatAutomation()
                        
                        with st.spinner("Realizando login..."):
                            if bot.login_with_javascript(cpf, senha):
                                st.success("Login realizado com sucesso!")
                                
                                # Processa tombamentos com base na opção selecionada
                                selected_indices = (
                                    selected_indices if opcao == "🎯 Processar selecionados"
                                    else None
                                )
                                
                                # Componentes de progresso
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                metrics_cols = st.columns(4)
                                tempo_col = metrics_cols[0].empty()
                                progresso_col = metrics_cols[1].empty()
                                sucessos_col = metrics_cols[2].empty()
                                falhas_col = metrics_cols[3].empty()
                                
                                # Processa tombamentos
                                for info in bot.processar_tombamentos(excel_path, selected_indices):
                                    if info['status'] == 'inicio':
                                        status_text.text("Iniciando processamento...")
                                        tempo_col.metric("Tempo Estimado", f"{info['tempo_estimado']//60} min")
                                        
                                    elif info['status'] == 'processando':
                                        # Atualiza barra de progresso
                                        progress_bar.progress(info['progresso'])
                                        
                                        # Atualiza status
                                        status_text.text(f"Processando {info['index']}/{info['total']}: {info['numero']}")
                                        
                                        # Atualiza métricas
                                        tempo_col.metric("Tempo Restante", f"{info['tempo_restante']//60:.0f} min")
                                        progresso_col.metric("Progresso", f"{info['progresso']*100:.1f}%")
                                        
                                    elif info['status'] == 'finalizando':
                                        status_text.text("Finalizando processamento...")
                                        
                                    elif info['status'] == 'concluido':
                                        progress_bar.progress(1.0)
                                        status_text.text("Processamento concluído!")
                                        tempo_col.metric("Tempo Total", f"{info['tempo_total']//60:.0f} min")
                                        sucessos_col.metric("Sucessos", f"{info['sucessos']}/{info['total']}")
                                        falhas_col.metric("Falhas", f"{info['total'] - info['sucessos']}")
                                        
                                        # Mostra resultados detalhados
                                        if os.path.exists('resultados_tombamento.xlsx'):
                                            df_resultados = pd.read_excel('resultados_tombamento.xlsx')
                                            st.write("Resultados do processamento:")
                                            st.dataframe(df_resultados)
                                        
                                        st.success("Processamento concluído com sucesso!")
                                        
                                    elif info['status'] == 'erro':
                                        st.error(f"Erro no processamento: {info['mensagem']}")
                                        break
                            else:
                                st.error("Falha no login!")
                                
                    except Exception as e:
                        st.error(f"Erro: {str(e)}")
                    
                    finally:
                        try:
                            bot.close()
                        except:
                            pass
                            
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {str(e)}")
                
                # Após processar Excel:
                st.session_state.pdfs_processados += 1
                st.session_state.tombamentos_realizados += len(df)
                st.session_state.log_atividades.append(
                    f"{datetime.now().strftime('%H:%M:%S')} - Processados {len(df)} números do Excel"
                )
    
    with tab3:
        st.header("Status do Sistema")
        
        # Inicializa contadores na sessão se não existirem
        if 'pdfs_processados' not in st.session_state:
            st.session_state.pdfs_processados = 0
        if 'tombamentos_realizados' not in st.session_state:
            st.session_state.tombamentos_realizados = 0
        if 'sucessos' not in st.session_state:
            st.session_state.sucessos = 0
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="PDFs/Excel Processados", 
                value=st.session_state.pdfs_processados
            )
        with col2:
            st.metric(
                label="Tombamentos Realizados", 
                value=st.session_state.tombamentos_realizados
            )
        with col3:
            taxa_sucesso = (
                f"{(st.session_state.sucessos / st.session_state.tombamentos_realizados * 100):.1f}%" 
                if st.session_state.tombamentos_realizados > 0 
                else "0%"
            )
            st.metric(label="Taxa de Sucesso", value=taxa_sucesso)
        
        # Log de atividades
        st.subheader("Log de Atividades")
        if 'log_atividades' not in st.session_state:
            st.session_state.log_atividades = []
        
        for log in st.session_state.log_atividades:
            st.text(log)

if __name__ == "__main__":
    main() 