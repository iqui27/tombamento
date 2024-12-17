from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time


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
    Lê o conteúdo de um arquivo PDF e retorna o texto completo
    """
    try:
        # Cria um objeto PDF reader
        pdf_reader = PdfReader(pdf_path)
        
        # Lista para armazenar o texto de todas as páginas
        text_content = []
        
        # Extrai o texto de cada página
        for page in pdf_reader.pages:
            text_content.append(page.extract_text())
        
        # Combina todo o texto em uma única string
        return '\n'.join(text_content)
        
    except Exception as e:
        print(f'Erro ao ler o arquivo PDF: {str(e)}')
        return ''

def process_pdf(pdf_path):
    """
    Processa o arquivo PDF e extrai os números de tombamento
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
        
        # Remove possíveis duplicatas mantendo a ordem
        tombamentos = list(dict.fromkeys(tombamentos))
        
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
        # Configurações do Chrome
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--start-maximized')
        
        # Inicializa o navegador Chrome
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                     options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

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

    def processar_tombamentos(self, excel_file):
        """
        Processa todos os números de tombamento do arquivo Excel
        """
        try:
            # Lê o arquivo Excel
            df = pd.read_excel(excel_file)
            
            # Navega até a tela correta
            if not self.navegar_para_dados_gerais():
                return False
            
            # Para cada número de tombamento
            total = len(df)
            for index, row in df.iterrows():
                numero = row['Numero_Tombamento']
                print(f"Processando tombamento {index + 1}/{total}: {numero}")
                
                if not self.preencher_tombamento(numero):
                    print(f"Falha ao processar tombamento {numero}")
                    continue
                
            # Após inserir todos, clica em Emitir
            try:
                print("Clicando no botão Emitir...")
                emitir_button = self.wait.until(
                    EC.element_to_be_clickable((
                        By.ID, "ctl00_ctl00_ctl00_CphBody_CphFormulario_BtnSalvar"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", emitir_button)
                print("✓ Clicou em Emitir")
                
                # Aguarda e clica no botão Sim do alerta
                print("Confirmando alerta...")
                confirmar_button = self.wait.until(
                    EC.element_to_be_clickable((
                        By.ID, "btnModalOk"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", confirmar_button)
                print("✓ Confirmou alerta")
                time.sleep(2)
                
                return True
                
            except Exception as e:
                print(f"Erro ao finalizar processo: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Erro ao processar arquivo: {str(e)}")
            return False

    def close(self):
        """
        Fecha o navegador
        """
        self.driver.quit()

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

    