import sqlite3
from datetime import datetime
import pandas as pd

class TombamentoDatabase:
    def __init__(self):
        self.db_path = 'tombamento.db'
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de processamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TIMESTAMP,
                usuario TEXT,
                tipo_arquivo TEXT,
                total_processado INTEGER,
                sucessos INTEGER,
                falhas INTEGER
            )
        ''')
        
        # Tabela de tombamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tombamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                processamento_id INTEGER,
                status TEXT,
                data_processamento TIMESTAMP,
                mensagem_erro TEXT,
                FOREIGN KEY (processamento_id) REFERENCES processamentos(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def registrar_processamento(self, usuario, tipo_arquivo, total, sucessos, falhas):
        """Registra um novo processamento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO processamentos 
            (data_hora, usuario, tipo_arquivo, total_processado, sucessos, falhas)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), usuario, tipo_arquivo, total, sucessos, falhas))
        
        processamento_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return processamento_id
    
    def registrar_tombamento(self, numero, processamento_id, status, mensagem_erro=None):
        """Registra um tombamento individual"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tombamentos 
            (numero, processamento_id, status, data_processamento, mensagem_erro)
            VALUES (?, ?, ?, ?, ?)
        ''', (numero, processamento_id, status, datetime.now(), mensagem_erro))
        
        conn.commit()
        conn.close()
    
    def get_estatisticas_gerais(self):
        """Retorna estatísticas gerais do sistema"""
        conn = sqlite3.connect(self.db_path)
        
        stats = pd.read_sql('''
            SELECT 
                COUNT(*) as total_processamentos,
                SUM(total_processado) as total_tombamentos,
                SUM(sucessos) as total_sucessos,
                SUM(falhas) as total_falhas,
                ROUND(CAST(SUM(sucessos) AS FLOAT) / 
                    CASE WHEN SUM(total_processado) = 0 THEN 1 
                    ELSE SUM(total_processado) END * 100, 2) as taxa_sucesso
            FROM processamentos
        ''', conn)
        
        conn.close()
        return stats.iloc[0]
    
    def get_ultimos_processamentos(self, limit=10):
        """Retorna os últimos processamentos"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql(f'''
            SELECT 
                data_hora,
                usuario,
                tipo_arquivo,
                total_processado,
                sucessos,
                falhas,
                ROUND(CAST(sucessos AS FLOAT) / 
                    CASE WHEN total_processado = 0 THEN 1 
                    ELSE total_processado END * 100, 2) as taxa_sucesso
            FROM processamentos
            ORDER BY data_hora DESC
            LIMIT {limit}
        ''', conn)
        
        conn.close()
        return df
    
    def get_tombamentos_status(self, status=None, limit=100):
        """Retorna os últimos tombamentos por status"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                t.numero,
                t.status,
                t.data_processamento,
                t.mensagem_erro,
                p.usuario
            FROM tombamentos t
            JOIN processamentos p ON t.processamento_id = p.id
        '''
        
        if status:
            query += f" WHERE t.status = '{status}'"
        
        query += f" ORDER BY t.data_processamento DESC LIMIT {limit}"
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df 
    
    def atualizar_processamento(self, processamento_id, sucessos, falhas):
        """Atualiza os resultados de um processamento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE processamentos 
            SET sucessos = ?, falhas = ?
            WHERE id = ?
        ''', (sucessos, falhas, processamento_id))
        
        conn.commit()
        conn.close()