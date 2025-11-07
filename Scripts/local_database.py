"""
Sistema de Banco de Dados Local com Sincronização
Módulo: Database Manager
Autor: Sistema de Reconhecimento Facial
"""

import sqlite3
import json
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalDatabase:
    """Gerenciador do banco de dados SQLite local"""

    def __init__(self, db_path: str = "local_database.db"):
        """
        Inicializa o banco de dados local

        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite
        """
        self.db_path = db_path
        self.init_database()
        self.init_attendance_history_table()  # NOVA TABELA DE HISTÓRICO

    def load_encodings_from_database(self):
        """Carrega encodings do banco de dados local"""
        print("Loading encodings from local database...")
        try:
            registros = self.local_db.get_all_registrations()

            self.encodeListKnown = []
            self.studentIds = []

            for registro in registros:
                if registro.get('encoding'):
                    # Deserializar encoding
                    encoding = deserialize_encoding(registro['encoding'])
                    if encoding is not None:
                        self.encodeListKnown.append(encoding)
                        self.studentIds.append(registro['id'])

            print(f"✅ Carregados {len(self.encodeListKnown)} encodings do banco local")

        except Exception as e:
            print(f"❌ Erro ao carregar encodings: {e}")
            self.encodeListKnown, self.studentIds = [], []

    def init_database(self):
        """Inicializa o banco de dados e cria as tabelas necessárias"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Criar tabela de registros
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS registrations (
                        id TEXT PRIMARY KEY UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        group_name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        event TEXT,
                        total_attendance INTEGER NOT NULL DEFAULT 0,
                        last_attendance_time TEXT,
                        image_path TEXT,
                        encoding BLOB,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        sync_status TEXT NOT NULL DEFAULT 'pending'
                    )
                ''')

                # Criar índices para melhor performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sync_status 
                    ON registrations(sync_status)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_updated_at 
                    ON registrations(updated_at)
                ''')

                conn.commit()
                logger.info("Banco de dados inicializado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise

    def init_attendance_history_table(self):
        """Cria tabela para armazenar histórico de presenças"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Criar tabela de histórico de presenças
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        user_name TEXT NOT NULL,
                        group_name TEXT NOT NULL,
                        phone TEXT,
                        event TEXT,
                        attendance_date TEXT NOT NULL,
                        total_attendance_at_time INTEGER,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Índice para buscar por usuário
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_id 
                    ON attendance_history(user_id)
                ''')
                
                # Índice para buscar por data
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_attendance_date 
                    ON attendance_history(attendance_date)
                ''')
                
                conn.commit()
                logger.info("Tabela de histórico de presenças criada com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao criar tabela de histórico: {e}")
            raise

    def insert_registration(self, registration_data: Dict[str, Any]) -> bool:
        """
        Insere um novo registro no banco de dados

        Args:
            registration_data: Dicionário com os dados do registro

        Returns:
            bool: True se inserido com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Preparar dados
                now = datetime.now().isoformat()

                cursor.execute('''
                    INSERT INTO registrations (
                        id, name, group_name, phone, event, total_attendance,
                        last_attendance_time, image_path, encoding,
                        created_at, updated_at, sync_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    registration_data.get('id'),
                    registration_data.get('name'),
                    registration_data.get('group'),
                    registration_data.get('phone'),
                    registration_data.get('event'),
                    registration_data.get('total_attendance', 0),
                    registration_data.get('last_attendance_time'),
                    registration_data.get('image_path'),
                    registration_data.get('encoding'),
                    now,
                    now,
                    'pending'
                ))

                conn.commit()
                logger.info(f"Registro inserido: {registration_data.get('id')}")
                return True

        except Exception as e:
            logger.error(f"Erro ao inserir registro: {e}")
            return False

    def update_registration(self, registration_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Atualiza um registro existente

        Args:
            registration_id: ID do registro a ser atualizado
            update_data: Dicionário com os dados a serem atualizados

        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Construir query dinamicamente baseada nos campos fornecidos
                set_clauses = []
                values = []

                for key, value in update_data.items():
                    if key != 'id':  # Não permitir atualização do ID
                        set_clauses.append(f"{key} = ?")
                        values.append(value)

                if not set_clauses:
                    return False

                # Adicionar timestamp de atualização e status de sincronização
                set_clauses.append("updated_at = ?")
                set_clauses.append("sync_status = ?")
                values.extend([datetime.now().isoformat(), 'pending'])
                values.append(registration_id)

                query = f'''
                    UPDATE registrations 
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                '''

                cursor.execute(query, values)
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Registro atualizado: {registration_id}")
                    return True
                else:
                    logger.warning(f"Nenhum registro encontrado para atualizar: {registration_id}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao atualizar registro: {e}")
            return False

    def get_registration(self, registration_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um registro pelo ID

        Args:
            registration_id: ID do registro

        Returns:
            Dict com os dados do registro ou None se não encontrado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM registrations WHERE id = ?
                ''', (registration_id,))

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar registro: {e}")
            return None

    def get_all_registrations(self) -> List[Dict[str, Any]]:
        """
        Busca todos os registros

        Returns:
            Lista com todos os registros
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM registrations ORDER BY created_at DESC
                ''')

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar registros: {e}")
            return []

    def get_pending_sync_registrations(self) -> List[Dict[str, Any]]:
        """
        Busca registros pendentes de sincronização

        Returns:
            Lista com registros pendentes de sincronização
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM registrations 
                    WHERE sync_status = 'pending'
                    ORDER BY updated_at ASC
                ''')

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar registros pendentes: {e}")
            return []

    def update_sync_status(self, registration_id: str, status: str) -> bool:
        """
        Atualiza o status de sincronização de um registro

        Args:
            registration_id: ID do registro
            status: Novo status ('pending', 'synced', 'error')

        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE registrations 
                    SET sync_status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, datetime.now().isoformat(), registration_id))

                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Erro ao atualizar status de sincronização: {e}")
            return False

    def delete_registration(self, registration_id: str) -> bool:
        """
        Remove um registro do banco de dados (SEM PRESERVAR HISTÓRICO)

        Args:
            registration_id: ID do registro a ser removido

        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM registrations WHERE id = ?
                ''', (registration_id,))

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Registro removido: {registration_id}")
                    return True
                else:
                    logger.warning(f"Nenhum registro encontrado para remover: {registration_id}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao remover registro: {e}")
            return False

    def save_to_history_before_delete(self, registration_id: str) -> bool:
        """
        Salva o registro de presença no histórico antes de deletar o usuário
        
        Args:
            registration_id: ID do usuário a ser deletado
            
        Returns:
            bool: True se o histórico foi salvo com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Buscar dados do usuário
                cursor.execute('''
                    SELECT id, name, group_name, phone, event, 
                           total_attendance, last_attendance_time
                    FROM registrations 
                    WHERE id = ?
                ''', (registration_id,))
                
                user_data = cursor.fetchone()
                
                if not user_data:
                    logger.warning(f"Usuário {registration_id} não encontrado")
                    return False
                
                # Inserir no histórico
                cursor.execute('''
                    INSERT INTO attendance_history (
                        user_id, user_name, group_name, phone, event,
                        attendance_date, total_attendance_at_time, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data[0],  # id
                    user_data[1],  # name
                    user_data[2],  # group_name
                    user_data[3],  # phone
                    user_data[4],  # event
                    user_data[6] or datetime.now().isoformat(),  # last_attendance_time
                    user_data[5],  # total_attendance
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"✅ Histórico salvo para usuário {registration_id}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
            return False

    def delete_user_keep_history(self, registration_id: str) -> bool:
        """
        Deleta um usuário do sistema mas mantém seu histórico de presenças
        
        Args:
            registration_id: ID do usuário a ser deletado
            
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            # 1. Primeiro salvar no histórico
            if not self.save_to_history_before_delete(registration_id):
                logger.error("Não foi possível salvar histórico antes de deletar")
                return False
            
            # 2. Depois deletar o usuário da tabela principal
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM registrations WHERE id = ?
                ''', (registration_id,))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Usuário {registration_id} deletado com histórico preservado")
                    return True
                else:
                    logger.warning(f"Nenhum usuário encontrado para deletar: {registration_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return False

    def get_user_attendance_history(self, registration_id: str) -> List[Dict[str, Any]]:
        """
        Busca todo o histórico de presenças de um usuário (mesmo deletado)
        
        Args:
            registration_id: ID do usuário
            
        Returns:
            Lista com histórico de presenças
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM attendance_history 
                    WHERE user_id = ?
                    ORDER BY attendance_date DESC
                ''', (registration_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return []

    def get_all_attendance_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca todo o histórico de presenças (incluindo usuários deletados)
        
        Args:
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista com histórico completo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM attendance_history 
                    ORDER BY attendance_date DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Erro ao buscar histórico completo: {e}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do banco de dados

        Returns:
            Dict com estatísticas do banco
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Total de registros
                cursor.execute('SELECT COUNT(*) FROM registrations')
                total_registrations = cursor.fetchone()[0]

                # Registros pendentes de sincronização
                cursor.execute('SELECT COUNT(*) FROM registrations WHERE sync_status = "pending"')
                pending_sync = cursor.fetchone()[0]

                # Registros sincronizados
                cursor.execute('SELECT COUNT(*) FROM registrations WHERE sync_status = "synced"')
                synced = cursor.fetchone()[0]

                # Registros com erro
                cursor.execute('SELECT COUNT(*) FROM registrations WHERE sync_status = "error"')
                error = cursor.fetchone()[0]
                
                # Total de histórico
                cursor.execute('SELECT COUNT(*) FROM attendance_history')
                total_history = cursor.fetchone()[0]

                return {
                    'total_registrations': total_registrations,
                    'pending_sync': pending_sync,
                    'synced': synced,
                    'error': error,
                    'total_history': total_history,
                    'database_path': self.db_path
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

    def get_recently_updated_registrations(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Busca registros que foram atualizados recentemente (independente do sync_status)

        Args:
            hours_back: Quantas horas atrás considerar como "recente"

        Returns:
            Lista de registros atualizados recentemente
        """
        try:
            # Calcular timestamp de corte
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            cutoff_timestamp = cutoff_time.isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM registrations 
                    WHERE updated_at > ? OR sync_status != 'synced'
                    ORDER BY updated_at DESC
                """, (cutoff_timestamp,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar registros atualizados recentemente: {e}")
            return []

    def mark_for_sync_after_edit(self, registration_id: str) -> bool:
        """
        Marca um registro para sincronização após edição
        Esta função deve ser chamada sempre que um registro é editado

        Args:
            registration_id: ID do registro editado

        Returns:
            bool: True se marcado com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE registrations 
                    SET sync_status = 'pending', updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), registration_id))

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Registro marcado para sincronização: {registration_id}")
                    return True
                else:
                    logger.warning(f"Registro não encontrado para marcar: {registration_id}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao marcar registro para sincronização: {e}")
            return False


# Função utilitária para serializar encodings faciais
def serialize_encoding(encoding) -> bytes:
    """
    Serializa um encoding facial para armazenamento no banco

    Args:
        encoding: Array numpy com o encoding facial

    Returns:
        bytes: Encoding serializado
    """
    try:
        return pickle.dumps(encoding)
    except Exception as e:
        logger.error(f"Erro ao serializar encoding: {e}")
        return b''


def deserialize_encoding(serialized_encoding: bytes):
    """
    Deserializa um encoding facial do banco de dados

    Args:
        serialized_encoding: Encoding serializado em bytes

    Returns:
        Array numpy com o encoding ou None se erro
    """
    try:
        if serialized_encoding:
            return pickle.loads(serialized_encoding)
        return None
    except Exception as e:
        logger.error(f"Erro ao deserializar encoding: {e}")
        return None


# ===== SCRIPT DE MIGRAÇÃO (Execute uma vez) =====
def migrate_existing_data_to_history():
    """
    Migra dados existentes para a tabela de histórico
    Execute este script UMA VEZ para migrar dados antigos
    """
    db = LocalDatabase()
    
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Buscar todos os usuários com presença registrada
            cursor.execute('''
                SELECT id, name, group_name, phone, event, 
                       total_attendance, last_attendance_time
                FROM registrations 
                WHERE total_attendance > 0 AND last_attendance_time IS NOT NULL
            ''')
            
            users = cursor.fetchall()
            migrated = 0
            
            for user in users:
                cursor.execute('''
                    INSERT INTO attendance_history (
                        user_id, user_name, group_name, phone, event,
                        attendance_date, total_attendance_at_time, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user[0], user[1], user[2], user[3], user[4],
                    user[6], user[5], datetime.now().isoformat()
                ))
                migrated += 1
            
            conn.commit()
            print(f"✅ {migrated} registros migrados para o histórico")
            
    except Exception as e:
        print(f"❌ Erro na migração: {e}")


# ===== EXEMPLO DE USO =====
if __name__ == "__main__":
    # Inicializar banco
    db = LocalDatabase()
    
    # Exemplo 1: Deletar usuário mantendo histórico
    print("\n=== EXEMPLO 1: Deletar usuário com histórico ===")
    success = db.delete_user_keep_history("144697")
    if success:
        print("✅ Usuário deletado, histórico preservado!")
    
    # Exemplo 2: Consultar histórico de um usuário
    print("\n=== EXEMPLO 2: Consultar histórico ===")
    history = db.get_user_attendance_history("144697")
    print(f"Histórico do usuário: {history}")
    
    # Exemplo 3: Consultar todo o histórico
    print("\n=== EXEMPLO 3: Todo o histórico ===")
    all_history = db.get_all_attendance_history(limit=10)
    print(f"Total de registros no histórico: {len(all_history)}")
    
    # Exemplo 4: Estatísticas
    print("\n=== EXEMPLO 4: Estatísticas ===")
    stats = db.get_database_stats()
    print(f"Estatísticas: {stats}")
    
    # Descomente para executar a migração (UMA VEZ):
    # migrate_existing_data_to_history()