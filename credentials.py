import json
import os
import re

class CredentialManager:
    def __init__(self, file_path='credentials.json'):
        self.file_path = file_path
        self.credentials = self.load_credentials()

    def format_cpf(self, cpf):
        """Formata CPF para o padrão XXX.XXX.XXX-XX"""
        # Remove todos os caracteres não numéricos
        cpf = re.sub(r'\D', '', cpf)
        
        if len(cpf) != 11:
            return None
            
        # Formata o CPF
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def save_credentials(self, cpf, senha):
        """Salva credenciais formatando o CPF"""
        formatted_cpf = self.format_cpf(cpf)
        if not formatted_cpf:
            raise ValueError("CPF inválido")
            
        self.credentials = {
            "cpf": formatted_cpf,
            "senha": senha
        }
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        with open(self.file_path, 'w') as f:
            json.dump(self.credentials, f)

    def load_credentials(self):
        """Carrega credenciais salvas"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar credenciais: {e}")
        return {}

    def get_credentials(self):
        """Retorna as credenciais salvas"""
        return self.credentials.get('cpf'), self.credentials.get('senha')

    def clear_credentials(self):
        """Remove as credenciais salvas"""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        self.credentials = {}
