from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
from datetime import datetime


import re
import pandas as pd
from PyPDF2 import PdfReader

def extract_tombamento_numbers(text):
    """
    Extrai números de tombamento do texto usando expressão regular.
    O padrão procura por números no formato 00000.000.000
    """
    # Padrão regex para encontrar números de tombamento
    pattern = r'\d{5}\.\d{3}\.\d{3}'
    
    # Encontra todos os números de tombamento no texto
    tombamentos = re.findall(pattern, text)
    
    return tombamentos

def read_pdf(pdf_path):
    """
    Lê o conteúdo de um arquivo PDF e retorna o texto completo.
    Tenta primeiro extrair texto diretamente, se falhar, usa OCR.
    """
    try:
        # Primeira tentativa: extrair texto diretamente
        pdf_reader = PdfReader(pdf_path)
        text_content = []
        
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text.strip():  # Verifica se há texto significativo
                text_content.append(text)
        
        # Se encontrou texto em todas as páginas, retorna
        if text_content and all(text.strip() for text in text_content):
            return '\n'.join(text_content)
        
        # Se não encontrou texto, tenta OCR
        print('Texto não encontrado diretamente. Tentando OCR...')
        return extract_text_with_ocr(pdf_path)
        
    except Exception as e:
        print(f'Erro ao ler o arquivo PDF: {str(e)}')
        return ''

def extract_text_with_ocr(pdf_path):
    """
    Extrai texto de um PDF usando OCR.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        import tempfile
        import os
        import platform
        
        text_content = []
        
        # Converte PDF para imagens
        print('Convertendo PDF para imagens...')
        with tempfile.TemporaryDirectory() as temp_dir:
            # No Mac não precisa especificar poppler_path
            if platform.system() == 'Windows':
                images = convert_from_path(pdf_path, poppler_path=r'C:\Program Files\poppler-xx\Library\bin')
            else:
                images = convert_from_path(pdf_path)
            
            # Processa cada página
            for i, image in enumerate(images, 1):
                print(f'Processando página {i} com OCR...')
                # Extrai texto da imagem usando OCR
                text = pytesseract.image_to_string(image, lang='por')
                text_content.append(text)
        
        return '\n'.join(text_content)
        
    except Exception as e:
        print(f'Erro ao processar OCR: {str(e)}')
        return ''

def process_pdf(pdf_path):
    """
    Processa o arquivo PDF e extrai os números de tombamento.
    Se não encontrar números no texto direto, tenta OCR.
    """
    try:
        # Lê o conteúdo do PDF
        print('Lendo o arquivo PDF...')
        content = read_pdf(pdf_path)
        
        if not content:
            print('Não foi possível extrair texto do PDF.')
            return []
        
        print('Extraindo números de tombamento...')
        # Extrai os números de tombamento
        tombamentos = extract_tombamento_numbers(content)
        
        # Se não encontrou números, tenta OCR
        if not tombamentos:
            print('Nenhum número encontrado no texto direto. Tentando OCR...')
            content_ocr = extract_text_with_ocr(pdf_path)
            if content_ocr:
                tombamentos = extract_tombamento_numbers(content_ocr)
        
        # Remove possíveis duplicatas mantendo a ordem
        tombamentos = list(dict.fromkeys(tombamentos))
        
        if not tombamentos:
            print('Nenhum número de tombamento encontrado, mesmo após OCR.')
            return []
        
        # Cria um DataFrame com os números de tombamento
        df = pd.DataFrame(tombamentos, columns=['Numero_Tombamento'])
        
        # Salva em um arquivo Excel
        output_file = 'numeros_tombamento.xlsx'
        df.to_excel(output_file, index=False)
        
        print(f'\nForam encontrados {len(tombamentos)} números de tombamento únicos.')
        print(f'Os dados foram salvos em {output_file}')
        
        return tombamentos
        
    except Exception as e:
        print(f'Erro ao processar o arquivo: {str(e)}')
        return []

def main():
    # Arquivo PDF a ser processado
    pdf_path = 'termo_movimentacao.pdf'  # Ajuste o nome do arquivo conforme necessário
    
    print('Iniciando processamento do PDF...')
    tombamentos = process_pdf(pdf_path)
    
    if tombamentos:
        print('\nPrimeiros 5 números encontrados:')
        for i, num in enumerate(tombamentos[:5], 1):
            print(f'{i}. {num}')

if __name__ == "__main__":
    main()

    
class SisgepatAutomation:
    def __init__(self):
        """
        Inicializa o navegador com configurações específicas para Mac ARM
        """
        try:
            # Configurações do Chrome
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Detecta arquitetura do sistema
            import platform
            is_arm = platform.processor().startswith('arm')
            
            if is_arm:
                # Configurações específicas para Mac ARM
                chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                chrome_options.add_argument('--disable-gpu')
            
            # Configuração do serviço com retry
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            for _ in range(3):  # Tenta 3 vezes
                try:
                    service = Service(ChromeDriverManager().install())
                    
                    # Inicializa o Chrome
                    self.driver = webdriver.Chrome(
                        service=service,
                        options=chrome_options
                    )
                    self.wait = WebDriverWait(self.driver, 10)
                    print("✓ Chrome inicializado com sucesso")
                    break
                    
                except Exception as e:
                    print(f"Tentativa de inicialização falhou: {str(e)}")
                    time.sleep(2)
            else:
                raise Exception("Não foi possível inicializar o Chrome após 3 tentativas")
                
        except Exception as e:
            print(f"Erro fatal ao inicializar Chrome: {str(e)}")
            raise

    def login(self, cpf, senha, ano="2024"):
        """
        Realiza o login no sistema
        """
        try:
            # Acessa a página
            self.driver.get("https://sisgepat.fazenda.df.gov.br/")
            
            # Aguarda e preenche os campos
            cpf_field = self.wait.until(EC.presence_of_element_located((By.ID, "TxtLogin")))
            cpf_field.send_keys(cpf)

            # Tenta localizar o campo de senha usando diferentes estratégias
            try:
                # Primeira tentativa: usando name e type
                senha_field = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='TxtSenha'][type='password']"))
                )
            except:
                try:
                    # Segunda tentativa: usando apenas o name
                    senha_field = self.wait.until(
                        EC.presence_of_element_located((By.NAME, "TxtSenha"))
                    )
                except:
                    # Terceira tentativa: usando a classe e type
                    senha_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'].grid_100"))
                    )

            # Limpa e preenche o campo
            senha_field.clear()
            time.sleep(1)  # Pequena pausa antes de inserir a senha
            senha_field.send_keys(senha)
            
            
            # Clica no botão de entrar
            entrar_button = self.driver.find_element(By.ID, "BtnEnviar")
            entrar_button.click()
            
            # Aguarda a página carregar
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"Erro no login: {str(e)}")
            return False
        
    def login_with_javascript(self, cpf, senha):
        """
        Tenta fazer login usando JavaScript Executor
        """
        try:
            # Acessa a página
            self.driver.get("https://sisgepat.fazenda.df.gov.br/")
            time.sleep(3)
            
            # Insere CPF via JavaScript
            self.driver.execute_script(
                f'document.getElementsByName("TxtLogin")[0].value = "{cpf}";'
            )
            
            # Insere Senha via JavaScript
            self.driver.execute_script(
                f'document.getElementsByName("TxtSenha")[0].value = "{senha}";'
            )
            
            # Clica no botão via JavaScript
            self.driver.execute_script(
                'document.getElementById("BtnEnviar").click();'
            )
            
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"Erro no login via JavaScript: {str(e)}")
            return False

    def navegar_para_dados_gerais(self):
        """
        Navega até a tela de Dados Gerais
        """
        try:
            try:
                print("Procurando link PAT...")
                # Aguarda mais tempo
                time.sleep(5)
                
                # Tenta diferentes estratégias para encontrar o elemento
                try:
                    # Tenta pelo texto
                    pat_link = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'PAT')]"))
                    )
                except:
                    try:
                        # Tenta pela classe
                        pat_link = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".mouseHover.text"))
                        )
                    except:
                        # Tenta pelo link completo
                        pat_link = self.driver.find_element(By.CSS_SELECTOR, 
                            "a#ct100_CphBody_RptModulos_ct100_RptSistemas_ct100_lnkModulo .spanText")

                # Tenta diferentes métodos de clique
                try:
                    # Tenta clique direto primeiro
                    pat_link.click()
                except:
                    try:
                        # Tenta com JavaScript
                        self.driver.execute_script("arguments[0].click();", pat_link)
                    except:
                        # Tenta encontrar o elemento pai e clicar nele
                        parent = pat_link.find_element(By.XPATH, "..")
                        self.driver.execute_script("arguments[0].click();", parent)

                print("✓ Clicou no PAT")
                time.sleep(5)  # Aguarda mais tempo após o clique
                
            except Exception as e:
                print(f"Erro ao clicar no PAT: {str(e)}")
                return False
            
            try:
                print("Navegando para DGCD - Dados Gerais...")
                # Navega diretamente para a URL
                self.driver.get("https://sisgepat.fazenda.df.gov.br/SIGGO/SISGEPAT/Paginas/070_Dados_Gerais/FrmDGComplementar.aspx")
                
                # Aguarda a página carregar
                time.sleep(5)
                
                print("✓ Navegou para DGCD - Dados Gerais")

                # Clica no botão Adicionar
                try:
                    print("Procurando botão Adicionar...")
                    add_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.ID, "ctl00_ctl00_ctl00_CphBody_CphFormulario_BtnAdicionar"
                        ))
                    )
                    self.driver.execute_script("arguments[0].click();", add_button)
                    print("✓ Clicou em Adicionar")
                    time.sleep(3)
                    return True
                
                except Exception as e:
                    print(f"Erro ao clicar no botão Adicionar: {str(e)}")
                    return False
            except Exception as e:
                print(f"Erro ao navegar para DGCD: {str(e)}")
                return False

        except Exception as e:
            print(f"Erro na navegação: {str(e)}")
            return False

    def preencher_tombamento(self, numero):
        """
        Preenche um número de tombamento
        """
        try:
            print(f"Preenchendo tombamento: {numero}")
            
            # Aguarda um pouco
            time.sleep(1)
            
            # Localiza o campo de tombamento usando o ID exato
            input_field = self.wait.until(
                EC.presence_of_element_located((
                    By.ID, "ctl00_ctl00_ctl00_CphBody_CphFormulario_CphFormularioInclusaoAlteracao_TxtTombamento"
                ))
            )
            
            # Limpa o campo
            input_field.clear()
            time.sleep(1)
            
            # Preenche usando JavaScript para garantir
            self.driver.execute_script(
                f'document.getElementById("ctl00_ctl00_ctl00_CphBody_CphFormulario_CphFormularioInclusaoAlteracao_TxtTombamento").value = "{numero}";'
            )
            
            # Dispara o evento de mudança para ativar validações do campo
            self.driver.execute_script(
                'document.getElementById("ctl00_ctl00_ctl00_CphBody_CphFormulario_CphFormularioInclusaoAlteracao_TxtTombamento").dispatchEvent(new Event("change"));'
            )
            
            time.sleep(1)

            # Procura e clica no botão ">>"
            add_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.ID, "ctl00_ctl00_ctl00_CphBody_CphFormulario_CphFormularioInclusaoAlteracao_BtnFRecursoAdd"
                ))
            )
            self.driver.execute_script("arguments[0].click();", add_button)
            
            print(f"✓ Preencheu tombamento: {numero}")
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"Erro ao preencher tombamento {numero}: {str(e)}")
            return False

    def processar_tombamentos(self, excel_file, selected_indices=None):
        try:
            # Lê o arquivo Excel
            df = pd.read_excel(excel_file)
            
            # Se tiver tombamentos selecionados, filtra o DataFrame
            if selected_indices is not None and len(selected_indices) > 0:
                df = df.iloc[selected_indices]
            
            total = len(df)
            
            
            
            # Navega até a tela correta
            if not self.navegar_para_dados_gerais():
                yield {'status': 'erro', 'mensagem': 'Erro na navegação inicial'}
                return
            
            time.sleep(5)
            sucessos = 0

            # Para cada número de tombamento
            for index, row in df.iterrows():
                numero = row['Numero_Tombamento']
                
                if index == 0:
                    time.sleep(3)
                
                progresso = min((index + 1) / total, 1.0)
                
                # Processa o tombamento
                try:
                    sucesso = self.preencher_tombamento(numero)
                    if sucesso:
                        sucessos += 1

                    # Retorna informações do processamento
                    yield {
                        'status': 'processando',
                        'numero': numero,
                        'index': index + 1,
                        'total': total,
                        'progresso': progresso,
                        'sucessos': sucessos,
                        'sucesso': sucesso,
                        'mensagem_erro': None if sucesso else 'Falha no preenchimento'
                    }
                    
                except Exception as e:
                    yield {
                        'status': 'processando',
                        'numero': numero,
                        'index': index + 1,
                        'total': total,
                        'progresso': progresso,
                        'sucesso': False,
                        'sucessos': sucessos,
                        'mensagem_erro': str(e)
                    }
                
                time.sleep(2)
            
             # Após inserir todos, clica em Emitir
            try:
                emitir_button = self.wait.until(
                    EC.element_to_be_clickable((
                        By.ID, "ctl00_ctl00_ctl00_CphBody_CphFormulario_BtnSalvar"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", emitir_button)
                
                # Aguarda e clica no botão Sim do alerta
                confirmar_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "btnModalOk"))
                )
                self.driver.execute_script("arguments[0].click();", confirmar_button)
                
                # Informa conclusão
                yield {
                    'status': 'concluido',
                    'total': total,
                    'mensagem': 'Processamento concluído com sucesso!'
                }
                
            except Exception as e:
                yield {
                    'status': 'erro',
                    'mensagem': f"Erro ao finalizar: {str(e)}"
                }
                
        except Exception as e:
            yield {
                'status': 'erro',
                'mensagem': f"Erro ao processar arquivo: {str(e)}"
            }

    def close(self):
        """
        Fecha o navegador com mais segurança
        """
        try:
            if hasattr(self, 'driver'):
                # Tenta fechar todas as janelas
                self.driver.quit()
                time.sleep(1)  # Pequena pausa para garantir que fechou
        except Exception as e:
            print(f"Erro ao fechar navegador: {str(e)}")
            # Tenta forçar o fechamento se necessário
            try:
                self.driver.quit()
            except:
                pass

def main():
    # Credenciais
    CPF = "058.842.031-01"
    SENHA = "Benicio28"
    ANO = "2024"
    
    # Arquivo com os números de tombamento
    EXCEL_FILE = "/Users/henrique/Documents/SECTI/DODF Bot/numeros_tombamento1.xlsx"
    
    # Inicia a automação
    bot = SisgepatAutomation()
    
    try:
        # Faz login
        if bot.login_with_javascript(CPF, SENHA):
            print("Login realizado com sucesso!")
            
            # Processa os números
            if bot.processar_tombamentos(EXCEL_FILE):
                print("Processamento concluído com sucesso!")
            else:
                print("Houve erro no processamento!")
            
        else:
            print("Falha no login!")
            
    finally:
        # Aguarda um pouco antes de fechar
        time.sleep(5)
        bot.close()

if __name__ == "__main__":
    main()

    