"""
Sistema de Banco de Dados Local com Sincronização
Módulo: Database Manager
Autor: Sistema de Reconhecimento Facial
"""

import sqlite3
import json
import pickle
import os
from datetime import datetime
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
        Remove um registro do banco de dados

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

                return {
                    'total_registrations': total_registrations,
                    'pending_sync': pending_sync,
                    'synced': synced,
                    'error': error,
                    'database_path': self.db_path
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}


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

def get_registration_by_id(self, registro_id):
    """Busca um registro específico pelo ID"""
    query = "SELECT * FROM registrations WHERE id = ?"
    result = self.execute_query(query, (registro_id,))
    return result[0] if result else None

def update_registration(self, registro_id, name, group_name, phone, sync_status):
    """Atualiza um registro existente"""
    query = '''UPDATE registrations 
               SET name = ?, group_name = ?, phone = ?, sync_status = ?, updated_at = ?
               WHERE id = ?'''
    from datetime import datetime
    updated_at = datetime.now().isoformat()
    return self.execute_query(query, (name, group_name, phone, sync_status, updated_at, registro_id))

def add_registration(self, name, group_name, phone, sync_status='pending'):
    """Adiciona um novo registro"""
    query = '''INSERT INTO registrations (name, group_name, phone, sync_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)'''
    from datetime import datetime
    now = datetime.now().isoformat()
    return self.execute_query(query, (name, group_name, phone, sync_status, now, now))

def delete_registration(self, registro_id):
    """Deleta um registro"""
    query = "DELETE FROM registrations WHERE id = ?"
    return self.execute_query(query, (registro_id,))
