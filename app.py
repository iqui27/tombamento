import streamlit as st
import pandas as pd
import time
from tomb import SisgepatAutomation, process_pdf
import os
from datetime import datetime
from database import TombamentoDatabase
from credentials import CredentialManager
import json

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

# Inicializa o banco de dados como variável global
db = TombamentoDatabase()

def init_session_state():
    """Inicializa variáveis do session_state"""
    if 'pdfs_processados' not in st.session_state:
        st.session_state.pdfs_processados = 0
    if 'tombamentos_realizados' not in st.session_state:
        st.session_state.tombamentos_realizados = 0
    if 'sucessos' not in st.session_state:
        st.session_state.sucessos = 0
    if 'log_atividades' not in st.session_state:
        st.session_state.log_atividades = []
    if 'num_sucessos' not in st.session_state:
        st.session_state.num_sucessos = 0
    if 'num_falhas' not in st.session_state:
        st.session_state.num_falhas = 0
    if 'saved_profiles' not in st.session_state:
        # Tentar carregar perfis salvos do arquivo
        try:
            with open('saved_profiles.json', 'r') as f:
                st.session_state.saved_profiles = json.load(f)
        except:
            st.session_state.saved_profiles = []
    if 'selected_profile' not in st.session_state:
        st.session_state.selected_profile = None

def save_profiles():
    """Salva os perfis em um arquivo"""
    try:
        with open('saved_profiles.json', 'w') as f:
            json.dump(st.session_state.saved_profiles, f)
    except Exception as e:
        st.error(f"Erro ao salvar perfis: {str(e)}")

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
    # Inicializa o session_state
    init_session_state()
    
    st.title("🤖 Sistema de Tombamento Automatizado")
    
    # Inicializa o gerenciador de credenciais
    cred_manager = CredentialManager()
    
    # Sidebar para login
    st.sidebar.title("🔐 Credenciais")
    
    # Carrega credenciais salvas
    saved_cpf, saved_senha = cred_manager.get_credentials()
    
    # Inicializa os perfis salvos no session_state se não existirem
    if 'saved_profiles' not in st.session_state:
        st.session_state.saved_profiles = []
    if 'selected_profile' not in st.session_state:
        st.session_state.selected_profile = None

    # Seletor de perfil e campos de entrada
    if st.session_state.saved_profiles:
        st.sidebar.subheader("📝 Perfis Salvos")
        profile_names = ["Selecione um perfil"] + [f"CPF: {p['cpf']}" for p in st.session_state.saved_profiles]
        
        index = 0
        if st.session_state.selected_profile:
            try:
                index = profile_names.index(f"CPF: {st.session_state.selected_profile['cpf']}")
            except ValueError:
                index = 0
        
        selected_profile = st.sidebar.selectbox(
            "Selecione um perfil",
            profile_names,
            index=index,
            key="profile_selector"
        )
        
        if selected_profile != "Selecione um perfil":
            selected_index = profile_names.index(selected_profile) - 1
            st.session_state.selected_profile = st.session_state.saved_profiles[selected_index]
            cpf = st.session_state.selected_profile['cpf']
            senha = st.session_state.selected_profile['senha']
        else:
            st.session_state.selected_profile = None
            cpf = st.sidebar.text_input("CPF", key="cpf_input", value=saved_cpf if saved_cpf else "")
            senha = st.sidebar.text_input("Senha", type="password", key="senha_input", value=saved_senha if saved_senha else "")
    else:
        cpf = st.sidebar.text_input("CPF", key="cpf_input", value=saved_cpf if saved_cpf else "")
        senha = st.sidebar.text_input("Senha", type="password", key="senha_input", value=saved_senha if saved_senha else "")
    
    # Formata o CPF enquanto digita
    if cpf and not st.session_state.selected_profile:
        try:
            formatted_cpf = cred_manager.format_cpf(cpf)
            if formatted_cpf and formatted_cpf != cpf:
                st.session_state.cpf_input = formatted_cpf
                st.rerun()
        except:
            pass

    # Ações para perfis
    if st.session_state.selected_profile:
        if st.sidebar.button("🗑️ Remover Perfil"):
            st.session_state.saved_profiles.remove(st.session_state.selected_profile)
            st.session_state.selected_profile = None
            save_profiles()  # Salva as alterações
            st.rerun()
    elif cpf and senha:  # Só mostra o botão de salvar perfil se tiver CPF e senha
        if st.sidebar.button("💾 Salvar como Perfil"):
            new_profile = {"cpf": cpf, "senha": senha}
            if new_profile not in st.session_state.saved_profiles:
                st.session_state.saved_profiles.append(new_profile)
                st.session_state.selected_profile = new_profile
                save_profiles()  # Salva as alterações
                st.sidebar.success("Perfil salvo com sucesso!")
                st.rerun()

    # Botões para gerenciar credenciais
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 Salvar Credenciais", key="save_cred"):
            try:
                if cpf and senha:
                    cred_manager.save_credentials(cpf, senha)
                    st.sidebar.success("Credenciais salvas!")
                else:
                    st.sidebar.warning("Preencha CPF e senha")
            except ValueError as e:
                st.sidebar.error(str(e))
    
    with col2:
        if st.button("🗑️ Limpar Credenciais", key="clear_cred"):
            cred_manager.clear_credentials()
            if 'cpf_input' in st.session_state:
                del st.session_state.cpf_input
            if 'senha_input' in st.session_state:
                del st.session_state.senha_input
            st.rerun()

    # Botões para gerenciar perfis
    if st.session_state.selected_profile:
        if st.sidebar.button("🗑️ Remover Perfil", key="remove_profile"):
            st.session_state.saved_profiles.remove(st.session_state.selected_profile)
            st.session_state.selected_profile = None
            st.rerun()
    else:
        if st.sidebar.button("💾 Salvar Perfil", key="save_profile"):
            if cpf and senha:
                new_profile = {"cpf": cpf, "senha": senha}
                if new_profile not in st.session_state.saved_profiles:
                    st.session_state.saved_profiles.append(new_profile)
                    st.session_state.selected_profile = new_profile
                    st.sidebar.success("Perfil salvo com sucesso!")
                    st.rerun()

    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Processamento de PDF", 
        "📑 Upload Excel", 
        "✏️ Editar TGCD",
        "📊 Status"
    ])
    
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
            
            try:
                # Processar PDFs
                with st.spinner("Extraindo números de tombamento..."):
                    df = process_multiple_pdfs(uploaded_pdfs)
                    
                if not df.empty:
                    st.success(f"Encontrados {len(df)} números de tombamento únicos!")
                    
                    # Carrega histórico de processamento se existir
                    df_historico = db.get_tombamentos_status()
                    if not df_historico.empty:
                        
                        sucessos = df_historico[df_historico['status'] == 'sucesso']['numero'].tolist()
                        falhas = df_historico[df_historico['status'] == 'falha']['numero'].tolist()
                        
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
                                    st.dataframe(df_historico[df_historico['status'] == 'sucesso'])
                                else:
                                    st.info("Nenhum tombamento processado com sucesso ainda.")
                            
                            with tab_falha:
                                if falhas:
                                    st.dataframe(df_historico[df_historico['status'] == 'falha'])
                                else:
                                    st.success("Nenhuma falha registrada!")
                    
                    # Opções de processamento
                    opcao = st.radio(
                        "Selecione o modo de processamento:",
                        ["✨ Processar todos",
                         "🎯 Processar selecionados",
                         "🔄 Reprocessar falhas",
                         "📝 Processar pendentes"],
                        key="pdf_radio"
                    )
                    # Inicializa selected_indices
                    selected_indices = None

                    if opcao == "🎯 Processar selecionados":
                        st.write("Selecione os números para processar:")
                        cols = st.columns(4)
                        selected_indices = []
                        
                        for idx, row in df.iterrows():
                            numero = row['Numero_Tombamento']
                            col_idx = idx % 4
                            if cols[col_idx].checkbox(
                                f"{numero}",
                                key=f"pdf_check_{idx}",
                                help="Marque para processar este número"
                            ):
                                selected_indices.append(idx)
                        
                        if not selected_indices:
                            st.warning("⚠️ Selecione pelo menos um número para processar")
                            return
                    
                    elif opcao == "🔄 Reprocessar falhas":
                         if df_historico.empty:
                            st.warning("⚠️ Não há histórico de processamentos anteriores")
                            return
                        
                         falhas = df_historico[df_historico['status'] == 'falha']['numero'].tolist()
                         df_temp = df[df['Numero_Tombamento'].isin(falhas)]
                         if df_temp.empty:
                             st.success("✨ Não há falhas para reprocessar!")
                             return
                         df = df_temp
                    
                    elif opcao == "📝 Processar pendentes":
                        if not df_historico.empty:
                            processados = df_historico['numero'].tolist()
                            df_temp = df[~df['Numero_Tombamento'].isin(processados)]
                            if df_temp.empty:
                                st.success("✨ Não há números pendentes para processar!")
                                return
                            df = df_temp
                    
                    # Mostrar preview e opção de download
                    with st.expander("🔍 Ver números a processar"):
                        st.dataframe(df)
                        st.info(f"Total de números a processar: {len(df)}")
                        excel_path = "numeros_tombamento_combinados.xlsx"
                        df.to_excel(excel_path, index=False)
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                label="📥 Baixar números em Excel",
                                data=f,
                                file_name="numeros_tombamento_combinados.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    # Botão de processamento
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        iniciar = st.button(
                            "▶️ Iniciar Processamento", 
                            type="primary",
                            help="Clique para iniciar o processamento dos números selecionados",
                            key="pdf_button"
                        )
                    with col2:
                        tempo_estimado = len(df) * 10
                        st.info(f"⏱️ Tempo estimado: {tempo_estimado//60} min")
                    
                    if iniciar:
                        if not cpf or not senha:
                            st.error("Por favor, preencha as credenciais primeiro!")
                            return
                        
                        try:
                            bot = SisgepatAutomation()
                            with st.spinner("Realizando login..."):
                                if bot.login_with_javascript(cpf, senha):
                                    st.success("Login realizado com sucesso!")
                                    st.spinner.text = "Processando tombamentos..."
                                    
                                    # Processa tombamentos com base na opção selecionada
                                    selected_indices = (
                                        selected_indices if opcao == "🎯 Processar selecionados"
                                        else None
                                    )

                                     # Calcula tempo estimado antes de iniciar
                                    total_registros = len(df)
                                    tempo_estimado = total_registros * 10 
                                    
                                    # Componentes de progresso
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    metrics_cols = st.columns(4)
                                    tempo_col = metrics_cols[0].empty()
                                    progresso_col = metrics_cols[1].empty()
                                    sucessos_col = metrics_cols[2].empty()
                                    falhas_col = metrics_cols[3].empty()
                                    
                                    # Botão de parar processamento
                                    stop_button = st.button("🛑 Parar Processamento", key="stop_btn")
                                    if stop_button:
                                        try:
                                            # Sinaliza a parada do processamento
                                            bot.stop_processing()
                                            
                                            # Salva o progresso atual
                                            status_text.text("Salvando progresso antes de parar...")
                                            bot.salvar_progresso()  # Supondo que existe este método no bot
                                            
                                            st.warning("Processamento interrompido e progresso salvo!")
                                            
                                            # Fecha o Chrome de forma limpa
                                            bot.close()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao parar processamento: {str(e)}")

                                    # Inicializa métricas
                                    tempo_col.metric("Tempo Estimado", f"{tempo_estimado//60} min")
                                    progresso_col.metric("Progresso", "0%")
                                    sucessos_col.metric("Sucessos", "0")
                                    falhas_col.metric("Falhas", "0")

# ...existing code...

                                     # Calcula tempo estimado antes de iniciar
                                    total_registros = len(df)
                                    tempo_estimado = total_registros * 10 
                                    
                                    # Componentes de progresso
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    metrics_cols = st.columns(4)
                                    tempo_col = metrics_cols[0].empty()
                                    progresso_col = metrics_cols[1].empty()
                                    sucessos_col = metrics_cols[2].empty()
                                    falhas_col = metrics_cols[3].empty()
                                    # ...existing code...

                                    # Inicializa métricas
                                    tempo_col.metric("Tempo Estimado", f"{tempo_estimado//60} min")
                                    progresso_col.metric("Progresso", "0%")
                                    sucessos_col.metric("Sucessos", "0")
                                    falhas_col.metric("Falhas", "0")
                                    # ...existing code...

                                    # Registra o processamento inicial no banco
                                    processamento_id = db.registrar_processamento(
                                        usuario=cpf,
                                        tipo_arquivo="PDF" if uploaded_pdfs else "Excel",
                                        total=total_registros,
                                        sucessos=0,
                                        falhas=0
                                    )

                                    # ...existing code...

                                    # Inicia o contador de tempo
                                    tempo_inicio = time.time()
                                    
                                    # Processa tombamentos
                                    for info in bot.processar_tombamentos(excel_path, selected_indices):
                                        if info['status'] == 'inicio':
                                            status_text.text("Iniciando processamento...")
                                            tempo_col.metric("Tempo Estimado", f"{info['tempo_estimado']//60} min")
                                            
                                        elif info['status'] == 'processando':
                                            # ...existing code...

                                            # Atualiza barra de progresso
                                            progress_bar.progress(info['progresso'])
                                            
                                            # ...existing code...

                                            # Atualiza status
                                            status_text.text(f"Processando {info['index']}/{info['total']}: {info['numero']}")
                                            # ...existing code...

                                            # Calcula tempo restante
                                            tempo_decorrido = time.time() - tempo_inicio
                                            if info['index'] > 1:
                                                tempo_por_item = tempo_decorrido / (info['index'])
                                                tempo_restante = tempo_por_item * (total_registros - info['index'])
                                            else:
                                                tempo_restante = tempo_estimado - tempo_decorrido


                                            # ...existing code...

                                            # Atualiza métricas
                                            tempo_col.metric(
                                                "Tempo Restante", 
                                                f"{max(0, int(tempo_restante))//60} min {max(0, int(tempo_restante))%60} seg"
                                            )
                                            progresso_col.metric("Progresso", f"{info['progresso']*100:.1f}%")
                                            # ...existing code...

                                            # Registra o tombamento no banco
                                            try:
                                                db.registrar_tombamento(
                                                    numero=info['numero'],
                                                    processamento_id=processamento_id,
                                                    status='sucesso' if info['sucesso'] else 'falha',
                                                    mensagem_erro=info.get('mensagem_erro')
                                                )
                                                
                                                # ...existing code...

                                                # Atualiza contadores
                                                if info['sucesso']:
                                                    st.session_state.num_sucessos += 1
                                                else:
                                                    st.session_state.num_falhas += 1
                                                
                                                # ...existing code...

                                                # Atualiza métricas na interface
                                                sucessos_col.metric("Sucessos", str(st.session_state.num_sucessos))
                                                falhas_col.metric("Falhas", str(st.session_state.num_falhas))
                                                
                                            except Exception as e:
                                                st.error(f"Erro ao registrar tombamento: {str(e)}")
                                                st.session_state.num_falhas += 1
                                                falhas_col.metric("Falhas", str(st.session_state.num_falhas))
                                            
                                        elif info['status'] == 'finalizando':
                                            status_text.text("Finalizando processamento...")
                                            
                                        elif info['status'] == 'concluido':
                                            progress_bar.progress(1.0)
                                            # ...existing code...

                                            # Calcula tempo total
                                            tempo_total = time.time() - tempo_inicio
                                            status_text.text("Processamento concluído!")
                                            tempo_col.metric(
                                                "Tempo Total", 
                                                f"{int(tempo_total)//60} min {int(tempo_total)%60} seg"
    )
                                            sucessos_col.metric("Sucessos", f"{st.session_state.num_sucessos}/{info['total']}")
                                            falhas_col.metric("Falhas", f"{info['total'] - st.session_state.num_sucessos}")
                                             # ...existing code...

                                            # Atualiza o processamento no banco
                                            # Atualiza o processamento no banco
                                            try:
                                                db.atualizar_processamento(
                                                    processamento_id,
                                                    sucessos=st.session_state.num_sucessos,  # ...existing code...

                                                    falhas=st.session_state.num_falhas      # ...existing code...

                                                )
                                                st.success(f"Processamento concluído com sucesso! Sucessos: {st.session_state.num_sucessos}, Falhas: {st.session_state.num_falhas}")
                                            except Exception as e:
                                                st.error(f"Erro ao atualizar processamento: {str(e)}")
                                                
                                            # ...existing code...

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
                                
                            # ...existing code...

                            # Atualiza estatísticas
                            st.session_state.pdfs_processados += len(uploaded_pdfs)
                            st.session_state.tombamentos_realizados += len(df)
                            st.session_state.log_atividades.append(
                                f"{datetime.now().strftime('%H:%M:%S')} - Processados {len(df)} números de {len(uploaded_pdfs)} PDFs"
                            )
                else:
                    st.warning("Nenhum número de tombamento encontrado nos PDFs!")
                    
            except Exception as e:
                st.error(f"Erro ao processar PDFs: {str(e)}")
    
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
                
                # ...existing code...

                # Carrega histórico de processamento se existir
                df_historico = db.get_tombamentos_status()
                if not df_historico.empty:
                    num_sucessos = df_historico[df_historico['status'] == 'sucesso']['numero'].tolist()
                    num_falhas = df_historico[df_historico['status'] == 'falha']['numero'].tolist()
                    
                    # ...existing code...

                    # Mostra estatísticas do histórico
                    with st.expander("📊 Ver histórico de processamento"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Processados com sucesso", len(num_sucessos))
                        with col2:
                            st.metric("Falhas", len(num_falhas))
                        with col3:
                            taxa = len(num_sucessos)/(len(num_sucessos) + len(num_falhas)) * 100 if num_sucessos or num_falhas else 0
                            st.metric("Taxa de Sucesso", f"{taxa:.1f}%")
                        
                        # ...existing code...

                        # Tabs para ver detalhes
                        tab_sucesso, tab_falha = st.tabs(["✅ Sucessos", "❌ Falhas"])
                        with tab_sucesso:
                            if num_sucessos:
                                st.dataframe(df_historico[df_historico['status'] == 'sucesso'])
                            else:
                                st.info("Nenhum tombamento processado com sucesso ainda.")
                        
                        with tab_falha:
                            if num_falhas:
                                st.dataframe(df_historico[df_historico['status'] == 'falha'])
                            else:
                                st.success("Nenhuma falha registrada!")
                
                # ...existing code...

                # Opções de processamento
                opcao = st.radio(
                    "Selecione o modo de processamento:",
                    ["✨ Processar todos",
                     "🎯 Processar selecionados",
                     "🔄 Reprocessar falhas",
                     "📝 Processar pendentes"]
                )
                
                if opcao == "🎯 Processar selecionados":
                    # ...existing code...

                    # Permite selecionar números específicos
                    st.write("Selecione os números para processar:")
                    
                    # ...existing code...

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
                    if df_historico.empty:
                        st.warning("⚠️ Não há histórico de processamentos anteriores")
                        return
                    
                    # ...existing code...

                    # Filtra apenas os números que falharam
                    num_falhas = df_historico[df_historico['status'] == 'falha']['numero'].tolist()
                    df_temp = df[df['Numero_Tombamento'].isin(num_falhas)]
                    if df_temp.empty:
                        st.success("✨ Não há falhas para reprocessar!")
                        return
                    df = df_temp
                
                elif opcao == "📝 Processar pendentes":
                    if not df_historico.empty:
                        # ...existing code...

                        # Filtra números que nunca foram processados
                        processados = df_historico['numero'].tolist()
                        df_temp = df[~df['Numero_Tombamento'].isin(processados)]
                        if df_temp.empty:
                            st.success("✨ Não há números pendentes para processar!")
                            return
                        df = df_temp
                
                # ...existing code...

                # Mostra preview dos números selecionados
                with st.expander("🔍 Ver números a processar"):
                    st.dataframe(df)
                    st.info(f"Total de números a processar: {len(df)}")
                
                # ...existing code...

                # Botão de processamento
                col1, col2 = st.columns([3, 1])
                with col1:
                    iniciar = st.button(
                        "▶️ Iniciar Processamento", 
                        type="primary",
                        help="Clique para iniciar o processamento dos números selecionados"
                    )
                with col2:
                    tempo_estimado = len(df) * 10  # ...existing code...

                    st.info(f"⏱️ Tempo estimado: {tempo_estimado//60} min")
                
                if iniciar:
                    # ...existing code...

                    # ... resto do código de processamento ...
                    
                    try:
                        bot = SisgepatAutomation()
                        
                        with st.spinner("Realizando login..."):
                            if bot.login_with_javascript(cpf, senha):
                                st.success("Login realizado com sucesso!")
                                st.spinner.text = "Processando tombamentos..."
                                
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
                                
                                # Botão de parar processamento
                                stop_button = st.button("🛑 Parar Processamento", key="stop_btn")
                                if stop_button:
                                    try:
                                        # Sinaliza a parada do processamento
                                        bot.stop_processing()
                                        
                                        # Salva o progresso atual
                                        status_text.text("Salvando progresso antes de parar...")
                                        bot.salvar_progresso()  # Supondo que existe este método no bot
                                        
                                        st.warning("Processamento interrompido e progresso salvo!")
                                        
                                        # Fecha o Chrome de forma limpa
                                        bot.close()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao parar processamento: {str(e)}")

                                # Processa tombamentos
                                for info in bot.processar_tombamentos(excel_path, selected_indices):
                                    if info['status'] == 'inicio':
                                        status_text.text("Iniciando processamento...")
                                        tempo_col.metric("Tempo Estimado", f"{info['tempo_estimado']//60} min")
                                        
                                    elif info['status'] == 'processando':
                                        # ...existing code...

                                        # Atualiza barra de progresso
                                        progress_bar.progress(info['progresso'])
                                        
                                        # ...existing code...

                                        # Atualiza status
                                        status_text.text(f"Processando {info['index']}/{info['total']}: {info['numero']}")
                                        
                                        # ...existing code...

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
                                        
                                        # ...existing code...

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
                        except Exception as e:
                            st.error(f"Erro ao fechar navegador: {str(e)}")
                            
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {str(e)}")
                
                # ...existing code...

                # Após processar Excel:
                st.session_state.pdfs_processados += 1
                st.session_state.tombamentos_realizados += len(df)
                st.session_state.log_atividades.append(
                    f"{datetime.now().strftime('%H:%M:%S')} - Processados {len(df)} números do Excel"
                )
    
    # ...existing code...

    # Nova aba para edição de TGCD
    with tab3:
        st.header("Editar TGCD Existente")
        
        col1, col2 = st.columns(2)
        with col1:
            numero_tgcd = st.text_input("Número da TGCD a editar")
            uploaded_files = st.file_uploader(
                "Arquivo Excel ou PDF com novos tombamentos",
                type=['xlsx', 'xls', 'pdf'],
                accept_multiple_files=True,
                key="tgcd_files"
            )
            
            if uploaded_files:
                try:
                    all_tombamentos = []
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    for idx, file in enumerate(uploaded_files):
                        progress_text.text(f"Processando arquivo {idx + 1}/{len(uploaded_files)}: {file.name}")
                        progress_bar.progress((idx + 1) / len(uploaded_files))
                        
                        if file.name.lower().endswith('.pdf'):
                            # Salvar PDF temporariamente
                            temp_pdf_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}.pdf"
                            with open(temp_pdf_path, "wb") as f:
                                f.write(file.getvalue())
                            
                            # Processa PDF usando a função existente
                            try:
                                tombamentos = process_pdf(temp_pdf_path)
                                if tombamentos:
                                    all_tombamentos.extend(tombamentos)
                                
                                # Limpa arquivo temporário
                                if os.path.exists(temp_pdf_path):
                                    os.remove(temp_pdf_path)
                                    
                            except Exception as e:
                                st.error(f"Erro ao processar PDF {file.name}: {str(e)}")
                        
                        else:  # Excel
                            df = pd.read_excel(file)
                            if 'Numero_Tombamento' in df.columns:
                                all_tombamentos.extend(df['Numero_Tombamento'].tolist())
                            else:
                                st.error(f"O arquivo Excel {file.name} deve ter uma coluna 'Numero_Tombamento'")
                    
                    # Remove duplicatas mantendo ordem
                    unique_tombamentos = list(dict.fromkeys(all_tombamentos))
                    
                    # Cria DataFrame final
                    df = pd.DataFrame(unique_tombamentos, columns=['Numero_Tombamento'])
                    if not df.empty:
                        st.success(f"Total de {len(df)} números de tombamento únicos encontrados!")
                        
                        # Preview dos dados
                        with st.expander("🔍 Ver números a processar"):
                            st.dataframe(df)
                            
                            # Opção para baixar Excel
                            excel_output = f"tombamentos_tgcd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            df.to_excel(excel_output, index=False)
                            with open(excel_output, "rb") as f:
                                st.download_button(
                                    "📥 Baixar Excel",
                                    f,
                                    file_name=excel_output,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                    else:
                        st.warning("Nenhum número de tombamento encontrado nos arquivos!")
                        
                except Exception as e:
                    st.error(f"Erro ao processar arquivos: {str(e)}")
        
        with col2:
            st.info("""
            ℹ️ Esta opção permite:
            - Adicionar novos tombamentos a uma TGCD existente
            - Processar os tombamentos em lotes
            - Parar e salvar o progresso a qualquer momento
            - Aceita arquivos PDF e Excel como entrada
            """)
            
            tamanho_lote = st.number_input(
                "Tamanho do Lote",
                min_value=1,
                value=100,
                help="Quantidade de tombamentos processados antes de salvar"
            )
        
        if uploaded_files and numero_tgcd:
            # Botões de controle
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                iniciar = st.button(
                    "▶️ Iniciar Processamento",
                    type="primary",
                    key="tgcd_start"
                )
            with col2:
                tempo_estimado = len(df) * 10 if 'df' in locals() else 0
                st.info(f"⏱️ ~{tempo_estimado//60} min")
            
            if iniciar:
                try:
                    bot = SisgepatAutomation()
                    
                    with st.spinner("Realizando login..."):
                        if bot.login_with_javascript(cpf, senha):
                            st.success("✅ Login realizado com sucesso!")
                            
                            # Containers para status
                            status_container = st.empty()
                            progress_container = st.progress(0)
                            metrics_cols = st.columns(3)
                            
                            progresso_col = metrics_cols[0].empty()
                            processados_col = metrics_cols[1].empty()
                            sucessos_col = metrics_cols[2].empty()
                            
                            # Botão de parada
                            stop_button = st.button("🛑 Parar Processamento", key="stop_tgcd")
                            
                            # Processa em lotes
                            for info in bot.processar_tombamentos_em_lotes(
                                excel_output,  # Usa o arquivo Excel gerado
                                tamanho_lote=tamanho_lote,
                                numero_tgcd=numero_tgcd
                            ):
                                if stop_button:
                                    bot.stop_processing()
                                    st.warning("⚠️ Parando processamento...")
                                    break
                                    
                                if info['status'] == 'processando':
                                    status_container.text(f"Processando: {info['numero']}")
                                    progress_container.progress(info['progresso_lote'])
                                    
                                    progresso_col.metric("Lote", f"{info['lote_atual']}/{info['total_lotes']}")
                                    processados_col.metric("Processados", f"{info['index']}/{info['total_lote']}")
                                    sucessos_col.metric("Sucessos", info['sucessos_lote'])
                                    
                                elif info['status'] in ['concluido', 'lote_concluido']:
                                    st.success(info['mensagem'])
                                
                                elif info['status'] == 'erro':
                                    st.error(info['mensagem'])
                        else:
                            st.error("❌ Falha no login!")
                            
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
                    
                finally:
                    if 'bot' in locals():
                        bot.close()
                        st.success("✅ Navegador fechado")
                        
                    # Limpa arquivo Excel temporário
                    if 'excel_output' in locals() and os.path.exists(excel_output):
                        os.remove(excel_output)

    # Rename existing tab3 to tab4 for Status tab
    with tab4:
        st.header("📊 Status do Sistema")
        
        # ...existing code...

        # Estatísticas gerais
        stats = db.get_estatisticas_gerais()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Processamentos", stats['total_processamentos'])
        with col2:
            st.metric("Total Tombamentos", stats['total_tombamentos'])
        with col3:
            st.metric("Taxa de Sucesso", f"{stats['taxa_sucesso']}%")
        with col4:
            st.metric("Total Falhas", stats['total_falhas'])
        
        # ...existing code...

        # Tabs para diferentes visualizações
        tab_processamentos, tab_sucessos, tab_falhas = st.tabs([
            "📋 Últimos Processamentos",
            "✅ Sucessos",
            "❌ Falhas"
        ])
        
        with tab_processamentos:
            st.subheader("Últimos Processamentos")
            df_proc = db.get_ultimos_processamentos()
            if not df_proc.empty:
                st.dataframe(df_proc, use_container_width=True)
            else:
                st.info("Nenhum processamento registrado ainda")
        
        with tab_sucessos:
            st.subheader("Últimos Tombamentos com Sucesso")
            df_sucess = db.get_tombamentos_status('sucesso')
            if not df_sucess.empty:
                st.dataframe(df_sucess, use_container_width=True)
            else:
                st.info("Nenhum tombamento com sucesso registrado ainda")
        
        with tab_falhas:
            st.subheader("Últimos Tombamentos com Falha")
            df_falhas = db.get_tombamentos_status('falha')
            if not df_falhas.empty:
                st.dataframe(df_falhas, use_container_width=True)
            else:
                st.success("Nenhuma falha registrada!")

if __name__ == "__main__":
    main()