"""
Sistema de Sincronização com Supabase - Versão Melhorada
Módulo: Sync Manager
Autor: Yago França
Melhorias: Sincronização de edições locais
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
from local_database import LocalDatabase, serialize_encoding, deserialize_encoding
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncManager:
    """Gerenciador de sincronização entre banco local e Supabase"""

    def __init__(self, supabase_url: str, supabase_key: str, storage_key: str = None):
        """
        Inicializa o gerenciador de sincronização

        Args:
            supabase_url: URL do projeto Supabase
            supabase_key: Chave de API do Supabase
            storage_key: Chave para acesso ao storage (opcional)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.storage_key = storage_key or supabase_key
        self.local_db = LocalDatabase()

        # Headers para requisições
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

        self.storage_headers = {
            'apikey': self.storage_key,
            'Authorization': f'Bearer {self.storage_key}',
        }

    def check_internet_connection(self) -> bool:
        """
        Verifica se há conexão com a internet

        Returns:
            bool: True se há conexão, False caso contrário
        """
        try:
            response = requests.get(f"{self.supabase_url}/rest/v1/",
                                    headers=self.headers, timeout=5)
            return response.status_code in [200, 401, 403]  # 401/403 indicam que o servidor está acessível
        except Exception as e:
            logger.warning(f"Sem conexão com a internet: {e}")
            return False

    def mark_record_for_sync(self, registration_id: str) -> bool:
        """
        Marca um registro para sincronização após edição local

        Args:
            registration_id: ID do registro editado

        Returns:
            bool: True se marcado com sucesso
        """
        try:
            return self.local_db.update_sync_status(registration_id, 'pending')
        except Exception as e:
            logger.error(f"Erro ao marcar registro para sincronização: {e}")
            return False

    def upload_to_supabase(self, registration_data: Dict[str, Any], is_update: bool = False) -> bool:
        """
        Envia um registro para o Supabase

        Args:
            registration_data: Dados do registro
            is_update: Se True, usa PATCH para atualização; se False, usa POST para inserção

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Preparar dados para o Supabase (remover campos específicos do banco local)
            supabase_data = {
                'id': registration_data['id'],
                'name': registration_data['name'],
                'group': registration_data['group_name'],
                'phone': registration_data['phone'],
                'event': registration_data.get('event'),
                'total_attendance': registration_data['total_attendance'],
                'last_attendance_time': registration_data.get('last_attendance_time'),
                'updated_at': datetime.now().isoformat()  # Timestamp de atualização
            }

            # Remover campos None
            supabase_data = {k: v for k, v in supabase_data.items() if v is not None}

            # URL base
            base_url = f"{self.supabase_url}/rest/v1/FaceAttendenceRealTime"

            if is_update:
                # Para atualizações, usar PATCH com filtro por ID
                url = f"{base_url}?id=eq.{registration_data['id']}"
                response = requests.patch(url, headers=self.headers, json=supabase_data)
            else:
                # Para inserções, usar POST com upsert
                upsert_headers = {**self.headers, 'Prefer': 'resolution=merge-duplicates'}
                response = requests.post(base_url, headers=upsert_headers, json=supabase_data)

            if response.status_code in [200, 201, 204]:
                action = "atualizado" if is_update else "inserido"
                logger.info(f"Registro {action} no Supabase: {registration_data['id']}")
                return True
            else:
                logger.error(f"Erro ao enviar para Supabase: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Erro ao enviar registro para Supabase: {e}")
            return False

    def upload_image_to_storage(self, registration_id: str, image_path: str) -> bool:
        """
        Faz upload de uma imagem para o Supabase Storage

        Args:
            registration_id: ID do registro
            image_path: Caminho local da imagem

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"Imagem não encontrada: {image_path}")
                return False

            # Preparar arquivo para upload
            filename = f"{registration_id}.png"

            with open(image_path, 'rb') as file:
                files = {'file': (filename, file, 'image/png')}

                # Headers específicos para upload
                upload_headers = {
                    'apikey': self.storage_key,
                    'Authorization': f'Bearer {self.storage_key}',
                }

                # URL para upload (usar upsert=true para sobrescrever se existir)
                url = f"{self.supabase_url}/storage/v1/object/storageforphotos/{filename}?upsert=true"

                response = requests.post(url, headers=upload_headers, files=files)

                if response.status_code in [200, 201]:
                    logger.info(f"Imagem enviada para storage: {filename}")
                    return True
                else:
                    logger.error(f"Erro ao enviar imagem: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao enviar imagem para storage: {e}")
            return False

    def download_from_supabase(self, last_sync_time: str = None) -> List[Dict[str, Any]]:
        """
        Baixa registros do Supabase que foram atualizados após um determinado tempo

        Args:
            last_sync_time: Timestamp da última sincronização (ISO format)

        Returns:
            Lista de registros baixados
        """
        try:
            url = f"{self.supabase_url}/rest/v1/FaceAttendenceRealTime"

            # Adicionar filtro de tempo se fornecido
            params = {}
            if last_sync_time:
                params['updated_at'] = f'gte.{last_sync_time}'

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Baixados {len(data)} registros do Supabase")
                return data
            else:
                logger.error(f"Erro ao baixar do Supabase: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Erro ao baixar registros do Supabase: {e}")
            return []

    def sync_pending_uploads(self) -> Tuple[int, int]:
        """
        Sincroniza registros pendentes de upload (incluindo edições)

        Returns:
            Tuple[int, int]: (sucessos, falhas)
        """
        if not self.check_internet_connection():
            logger.warning("Sem conexão com a internet. Sincronização adiada.")
            return 0, 0

        pending_registrations = self.local_db.get_pending_sync_registrations()
        successes = 0
        failures = 0

        for registration in pending_registrations:
            try:
                # Verificar se o registro já existe no Supabase
                existing_record = self.check_record_exists_remote(registration['id'])
                is_update = existing_record is not None

                # Tentar enviar dados
                if self.upload_to_supabase(registration, is_update=is_update):
                    # Se há imagem, tentar enviar também
                    if registration.get('image_path') and os.path.exists(registration['image_path']):
                        if self.upload_image_to_storage(registration['id'], registration['image_path']):
                            logger.info(f"Imagem sincronizada: {registration['id']}")
                        else:
                            logger.warning(f"Falha ao sincronizar imagem: {registration['id']}")

                    # Marcar como sincronizado
                    self.local_db.update_sync_status(registration['id'], 'synced')
                    successes += 1

                    action = "atualizado" if is_update else "criado"
                    logger.info(f"Registro {action} com sucesso: {registration['id']}")
                else:
                    # Marcar como erro
                    self.local_db.update_sync_status(registration['id'], 'error')
                    failures += 1

                # Pequena pausa entre uploads para não sobrecarregar
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Erro ao sincronizar registro {registration['id']}: {e}")
                self.local_db.update_sync_status(registration['id'], 'error')
                failures += 1

        logger.info(f"Sincronização de uploads concluída: {successes} sucessos, {failures} falhas")
        return successes, failures

    def check_record_exists_remote(self, registration_id: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se um registro existe no Supabase

        Args:
            registration_id: ID do registro

        Returns:
            Dict com dados do registro se existir, None caso contrário
        """
        try:
            url = f"{self.supabase_url}/rest/v1/FaceAttendenceRealTime?id=eq.{registration_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            else:
                logger.error(f"Erro ao verificar registro remoto: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erro ao verificar existência do registro: {e}")
            return None

    def sync_downloads(self, last_sync_time: str = None) -> int:
        """
        Sincroniza downloads do Supabase para o banco local

        Args:
            last_sync_time: Timestamp da última sincronização

        Returns:
            int: Número de registros baixados e atualizados
        """
        if not self.check_internet_connection():
            logger.warning("Sem conexão com a internet. Download adiado.")
            return 0

        remote_data = self.download_from_supabase(last_sync_time)
        updated_count = 0

        for remote_record in remote_data:
            try:
                # Verificar se o registro já existe localmente
                local_record = self.local_db.get_registration(remote_record['id'])

                if local_record:
                    # Verificar se o registro remoto é mais recente
                    remote_time = datetime.fromisoformat(remote_record.get('updated_at', remote_record.get('last_attendance_time', '1970-01-01')))
                    local_time = datetime.fromisoformat(local_record.get('updated_at', '1970-01-01'))

                    if remote_time > local_time:
                        # Atualizar registro local
                        update_data = {
                            'name': remote_record.get('name'),
                            'group_name': remote_record.get('group'),
                            'phone': remote_record.get('phone'),
                            'event': remote_record.get('event'),
                            'total_attendance': remote_record.get('total_attendance', 0),
                            'last_attendance_time': remote_record.get('last_attendance_time'),
                            'updated_at': remote_record.get('updated_at'),
                            'sync_status': 'synced'
                        }

                        if self.local_db.update_registration(remote_record['id'], update_data):
                            updated_count += 1
                            logger.info(f"Registro atualizado do remoto: {remote_record['id']}")
                else:
                    # Inserir novo registro
                    new_record = {
                        'id': remote_record['id'],
                        'name': remote_record.get('name'),
                        'group': remote_record.get('group'),
                        'phone': remote_record.get('phone'),
                        'event': remote_record.get('event'),
                        'total_attendance': remote_record.get('total_attendance', 0),
                        'last_attendance_time': remote_record.get('last_attendance_time'),
                        'updated_at': remote_record.get('updated_at')
                    }

                    if self.local_db.insert_registration(new_record):
                        # Marcar como sincronizado
                        self.local_db.update_sync_status(remote_record['id'], 'synced')
                        updated_count += 1
                        logger.info(f"Novo registro baixado: {remote_record['id']}")

            except Exception as e:
                logger.error(f"Erro ao processar registro remoto {remote_record.get('id', 'unknown')}: {e}")

        logger.info(f"Download concluído: {updated_count} registros atualizados")
        return updated_count

    def sync_edited_records(self) -> Tuple[int, int]:
        """
        Sincroniza especificamente registros que foram editados localmente

        Returns:
            Tuple[int, int]: (sucessos, falhas)
        """
        logger.info("Iniciando sincronização de registros editados...")

        if not self.check_internet_connection():
            logger.warning("Sem conexão com a internet. Sincronização de edições adiada.")
            return 0, 0

        # Buscar todos os registros que não estão sincronizados
        try:
            # Tentar usar o método se existir
            if hasattr(self.local_db, 'get_recently_updated_registrations'):
                edited_records = self.local_db.get_recently_updated_registrations()
            else:
                # Fallback: usar método alternativo
                edited_records = self.get_unsynced_records_fallback()
        except Exception as e:
            logger.error(f"Erro ao buscar registros editados: {e}")
            return 0, 0

        successes = 0
        failures = 0

        for record in edited_records:
            try:
                # Forçar atualização no Supabase
                if self.upload_to_supabase(record, is_update=True):
                    self.local_db.update_sync_status(record['id'], 'synced')
                    successes += 1
                    logger.info(f"Registro editado sincronizado: {record['id']}")
                else:
                    self.local_db.update_sync_status(record['id'], 'error')
                    failures += 1

                time.sleep(0.1)  # Pausa entre requisições

            except Exception as e:
                logger.error(f"Erro ao sincronizar registro editado {record['id']}: {e}")
                self.local_db.update_sync_status(record['id'], 'error')
                failures += 1

        logger.info(f"Sincronização de edições concluída: {sucessos} sucessos, {failures} falhas")
        return sucessos, failures

    def get_unsynced_records_fallback(self) -> List[Dict[str, Any]]:
        """
        Método alternativo para buscar registros não sincronizados
        quando o método principal não está disponível

        Returns:
            Lista de registros não sincronizados
        """
        try:
            # Usar métodos que já existem na sua LocalDatabase
            all_registrations = self.local_db.get_all_registrations()

            # Filtrar apenas os que não estão sincronizados
            unsynced = []
            for reg in all_registrations:
                if reg.get('sync_status') != 'synced':
                    unsynced.append(reg)

            logger.info(f"Encontrados {len(unsynced)} registros não sincronizados")
            return unsynced

        except Exception as e:
            logger.error(f"Erro no método fallback: {e}")
            return []

    def full_sync(self) -> Dict[str, Any]:
        """
        Executa uma sincronização completa (upload, edições e download)

        Returns:
            Dict com estatísticas da sincronização
        """
        logger.info("Iniciando sincronização completa...")

        if not self.check_internet_connection():
            return {
                'status': 'error',
                'message': 'Sem conexão com a internet',
                'uploads_success': 0,
                'uploads_failed': 0,
                'edits_success': 0,
                'edits_failed': 0,
                'downloads': 0
            }

        # 1. Sincronizar uploads pendentes
        uploads_success, uploads_failed = self.sync_pending_uploads()

        # 2. Sincronizar registros editados
        edits_success, edits_failed = self.sync_edited_records()

        # 3. Baixar atualizações remotas
        downloads = self.sync_downloads()

        result = {
            'status': 'success',
            'message': 'Sincronização completa concluída',
            'uploads_success': uploads_success,
            'uploads_failed': uploads_failed,
            'edits_success': edits_success,
            'edits_failed': edits_failed,
            'downloads': downloads,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Sincronização completa finalizada: {result}")
        return result

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual da sincronização

        Returns:
            Dict com informações de status
        """
        stats = self.local_db.get_database_stats()
        has_internet = self.check_internet_connection()

        return {
            'has_internet': has_internet,
            'total_registrations': stats.get('total_registrations', 0),
            'pending_sync': stats.get('pending_sync', 0),
            'synced': stats.get('synced', 0),
            'sync_errors': stats.get('error', 0),
            'last_check': datetime.now().isoformat()
        }


# Função utilitária para configuração automática
def create_sync_manager_from_config() -> SyncManager:
    """
    Cria um SyncManager usando as configurações do código original

    Returns:
        SyncManager configurado
    """
    SUPABASE_URL = "https://jtqxscwmjjaandwujsxq.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
    STORAGE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTE0MzYwNSwiZXhwIjoyMDY0NzE5NjA1fQ.yPXNbMP0-u3uwBTX8n-ymKIxH0S1mJV9D4TjLRC7DNk"

    return SyncManager(SUPABASE_URL, SUPABASE_KEY, STORAGE_KEY)


if __name__ == "__main__":
    # Teste da versão melhorada
    sync_manager = create_sync_manager_from_config()

    print("Testando conexão com a internet...")
    has_internet = sync_manager.check_internet_connection()
    print(f"Conexão: {'Disponível' if has_internet else 'Indisponível'}")

    print("Testando status de sincronização...")
    status = sync_manager.get_sync_status()
    print(f"Status: {status}")

    if has_internet:
        print("Testando sincronização completa (incluindo edições)...")
        result = sync_manager.full_sync()
        print(f"Resultado: {result}")