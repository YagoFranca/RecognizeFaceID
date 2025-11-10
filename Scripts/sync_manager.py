"""
Sistema de Sincronização com Supabase
Módulo: Sync Manager
Autor: Yago França
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

    def upload_to_supabase(self, registration_data: Dict[str, Any]) -> bool:
        """
        Envia um registro para o Supabase

        Args:
            registration_data: Dados do registro

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
                'last_attendance_time': registration_data.get('last_attendance_time')
            }

            # Remover campos None
            supabase_data = {k: v for k, v in supabase_data.items() if v is not None}

            # Fazer upsert no Supabase
            url = f"{self.supabase_url}/rest/v1/FaceAttendenceRealTime"
            response = requests.post(url, headers=self.headers, json=supabase_data)

            if response.status_code in [200, 201]:
                logger.info(f"Registro enviado para Supabase: {registration_data['id']}")
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

                # URL para upload
                url = f"{self.supabase_url}/storage/v1/object/storageforphotos/{filename}"

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
                params['last_attendance_time'] = f'gte.{last_sync_time}'

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
        Sincroniza registros pendentes de upload

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
                # Tentar enviar dados
                if self.upload_to_supabase(registration):
                    # Se há imagem, tentar enviar também
                    if registration.get('image_path') and os.path.exists(registration['image_path']):
                        if self.upload_image_to_storage(registration['id'], registration['image_path']):
                            logger.info(f"Imagem sincronizada: {registration['id']}")
                        else:
                            logger.warning(f"Falha ao sincronizar imagem: {registration['id']}")

                    # Marcar como sincronizado
                    self.local_db.update_sync_status(registration['id'], 'synced')
                    successes += 1
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

        logger.info(f"Sincronização concluída: {successes} sucessos, {failures} falhas")
        return successes, failures

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
                    remote_time = datetime.fromisoformat(remote_record.get('last_attendance_time', '1970-01-01'))
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
                        'last_attendance_time': remote_record.get('last_attendance_time')
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

    def full_sync(self) -> Dict[str, Any]:
        """
        Executa uma sincronização completa (upload e download)

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
                'downloads': 0
            }

        # Fazer uploads primeiro
        uploads_success, uploads_failed = self.sync_pending_uploads()

        # Depois fazer downloads
        downloads = self.sync_downloads()

        result = {
            'status': 'success',
            'message': 'Sincronização concluída',
            'uploads_success': uploads_success,
            'uploads_failed': uploads_failed,
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
    SUPABASE_URL = "https://bxdykjxoskysmywtdfoa.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4ZHlranhvc2t5c215d3RkZm9hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1Njk1OTAsImV4cCI6MjA3MDE0NTU5MH0.qsyqdfyBxjdKQNGz6Y9eVxMr633XBgZxuIyGt7OiS2c"
    STORAGE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4ZHlranhvc2t5c215d3RkZm9hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDU2OTU5MCwiZXhwIjoyMDcwMTQ1NTkwfQ.hGsOdmuVcO7AtKTqrR8rA-b0Y8tYeymt-Dzws20VSZU"

    return SyncManager(SUPABASE_URL, SUPABASE_KEY, STORAGE_KEY)


if __name__ == "__main__":
    # Teste básico do sistema de sincronização
    sync_manager = create_sync_manager_from_config()

    print("Testando conexão com a internet...")
    has_internet = sync_manager.check_internet_connection()
    print(f"Conexão: {'Disponível' if has_internet else 'Indisponível'}")

    print("Testando status de sincronização...")
    status = sync_manager.get_sync_status()
    print(f"Status: {status}")

    if has_internet:
        print("Testando sincronização completa...")
        result = sync_manager.full_sync()
        print(f"Resultado: {result}")

