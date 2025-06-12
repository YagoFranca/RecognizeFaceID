"""
Testes do Sistema de Banco Local e Sincronização
Módulo: Test Suite
Autor: Yago França
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime
import sqlite3
from local_database import LocalDatabase, serialize_encoding, deserialize_encoding
from sync_manager import SyncManager
import numpy as np


class TestLocalDatabase(unittest.TestCase):
    """Testes para o banco de dados local"""

    def setUp(self):
        """Configuração antes de cada teste"""
        # Criar banco temporário
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = LocalDatabase(self.db_path)

        # Dados de teste
        self.test_data = {
            'id': 'test123',
            'name': 'João Silva',
            'group': 'Grupo A',
            'phone': '11999999999',
            'event': 'Evento Teste',
            'total_attendance': 1,
            'last_attendance_time': datetime.now().isoformat()
        }

    def tearDown(self):
        """Limpeza após cada teste"""
        shutil.rmtree(self.temp_dir)

    def test_database_initialization(self):
        """Testa a inicialização do banco de dados"""
        self.assertTrue(os.path.exists(self.db_path))

        # Verificar se as tabelas foram criadas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='registrations'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)

    def test_insert_registration(self):
        """Testa a inserção de registros"""
        success = self.db.insert_registration(self.test_data)
        self.assertTrue(success)

        # Verificar se foi inserido
        result = self.db.get_registration('test123')
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'João Silva')
        self.assertEqual(result['sync_status'], 'pending')

    def test_update_registration(self):
        """Testa a atualização de registros"""
        # Inserir primeiro
        self.db.insert_registration(self.test_data)

        # Atualizar
        update_data = {'name': 'João Santos', 'total_attendance': 2}
        success = self.db.update_registration('test123', update_data)
        self.assertTrue(success)

        # Verificar atualização
        result = self.db.get_registration('test123')
        self.assertEqual(result['name'], 'João Santos')
        self.assertEqual(result['total_attendance'], 2)
        self.assertEqual(result['sync_status'], 'pending')

    def test_get_all_registrations(self):
        """Testa a busca de todos os registros"""
        # Inserir múltiplos registros
        for i in range(3):
            data = self.test_data.copy()
            data['id'] = f'test{i}'
            data['name'] = f'Usuário {i}'
            self.db.insert_registration(data)

        # Buscar todos
        all_registrations = self.db.get_all_registrations()
        self.assertEqual(len(all_registrations), 3)

    def test_get_pending_sync_registrations(self):
        """Testa a busca de registros pendentes de sincronização"""
        # Inserir registros com diferentes status
        data1 = self.test_data.copy()
        data1['id'] = 'pending1'
        self.db.insert_registration(data1)

        data2 = self.test_data.copy()
        data2['id'] = 'synced1'
        self.db.insert_registration(data2)
        self.db.update_sync_status('synced1', 'synced')

        # Buscar pendentes
        pending = self.db.get_pending_sync_registrations()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['id'], 'pending1')

    def test_update_sync_status(self):
        """Testa a atualização do status de sincronização"""
        self.db.insert_registration(self.test_data)

        success = self.db.update_sync_status('test123', 'synced')
        self.assertTrue(success)

        result = self.db.get_registration('test123')
        self.assertEqual(result['sync_status'], 'synced')

    def test_delete_registration(self):
        """Testa a remoção de registros"""
        self.db.insert_registration(self.test_data)

        success = self.db.delete_registration('test123')
        self.assertTrue(success)

        result = self.db.get_registration('test123')
        self.assertIsNone(result)

    def test_database_stats(self):
        """Testa as estatísticas do banco"""
        # Inserir registros com diferentes status
        for i in range(5):
            data = self.test_data.copy()
            data['id'] = f'test{i}'
            self.db.insert_registration(data)

        # Marcar alguns como sincronizados
        self.db.update_sync_status('test0', 'synced')
        self.db.update_sync_status('test1', 'synced')
        self.db.update_sync_status('test2', 'error')

        stats = self.db.get_database_stats()
        self.assertEqual(stats['total_registrations'], 5)
        self.assertEqual(stats['pending_sync'], 2)
        self.assertEqual(stats['synced'], 2)
        self.assertEqual(stats['error'], 1)


class TestEncodingSerialization(unittest.TestCase):
    """Testes para serialização de encodings faciais"""

    def test_serialize_deserialize_encoding(self):
        """Testa a serialização e deserialização de encodings"""
        # Criar um encoding fake (array numpy)
        fake_encoding = np.random.rand(128)

        # Serializar
        serialized = serialize_encoding(fake_encoding)
        self.assertIsInstance(serialized, bytes)
        self.assertGreater(len(serialized), 0)

        # Deserializar
        deserialized = deserialize_encoding(serialized)
        self.assertIsNotNone(deserialized)

        # Verificar se são iguais
        np.testing.assert_array_equal(fake_encoding, deserialized)

    def test_serialize_none_encoding(self):
        """Testa serialização de encoding None"""
        serialized = serialize_encoding(None)
        self.assertEqual(serialized, b'')

        deserialized = deserialize_encoding(b'')
        self.assertIsNone(deserialized)


class TestSyncManager(unittest.TestCase):
    """Testes para o gerenciador de sincronização"""

    def setUp(self):
        """Configuração antes de cada teste"""
        # Usar configurações de teste (URLs fake)
        self.sync_manager = SyncManager(
            "https://fake-url.supabase.co",
            "fake-key",
            "fake-storage-key"
        )

        # Criar banco temporário
        self.temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(self.temp_dir, "test_sync.db")
        self.sync_manager.local_db = LocalDatabase(db_path)

    def tearDown(self):
        """Limpeza após cada teste"""
        shutil.rmtree(self.temp_dir)

    def test_check_internet_connection_fake(self):
        """Testa verificação de conexão (deve falhar com URL fake)"""
        has_internet = self.sync_manager.check_internet_connection()
        self.assertFalse(has_internet)  # URL fake deve falhar

    def test_get_sync_status(self):
        """Testa obtenção do status de sincronização"""
        status = self.sync_manager.get_sync_status()

        self.assertIn('has_internet', status)
        self.assertIn('total_registrations', status)
        self.assertIn('pending_sync', status)
        self.assertIn('synced', status)
        self.assertIn('sync_errors', status)
        self.assertIn('last_check', status)


def run_demonstration():
    """Executa uma demonstração do sistema"""
    print("=" * 60)
    print("DEMONSTRAÇÃO DO SISTEMA DE BANCO LOCAL E SINCRONIZAÇÃO")
    print("=" * 60)

    # Criar banco de demonstração
    demo_db = LocalDatabase("demo_database.db")

    print("\n1. Inserindo registros de demonstração...")
    demo_data = [
        {
            'id': 'demo001',
            'name': 'Maria Silva',
            'group': 'Administração',
            'phone': '11987654321',
            'event': 'Reunião Mensal',
            'total_attendance': 1
        },
        {
            'id': 'demo002',
            'name': 'João Santos',
            'group': 'Vendas',
            'phone': '11876543210',
            'event': 'Treinamento',
            'total_attendance': 2
        },
        {
            'id': 'demo003',
            'name': 'Ana Costa',
            'group': 'Marketing',
            'phone': '11765432109',
            'event': 'Workshop',
            'total_attendance': 1
        }
    ]

    for data in demo_data:
        success = demo_db.insert_registration(data)
        print(f"   Inserido: {data['name']} - {'✅' if success else '❌'}")

    print("\n2. Estatísticas do banco local:")
    stats = demo_db.get_database_stats()
    print(f"   Total de registros: {stats['total_registrations']}")
    print(f"   Pendentes de sincronização: {stats['pending_sync']}")
    print(f"   Sincronizados: {stats['synced']}")
    print(f"   Com erro: {stats['error']}")

    print("\n3. Listando todos os registros:")
    all_registrations = demo_db.get_all_registrations()
    for reg in all_registrations:
        status_icon = {"pending": "⏳", "synced": "✅", "error": "❌"}.get(reg['sync_status'], "❓")
        print(f"   {status_icon} {reg['name']} | {reg['group_name']} | {reg['phone']} | ID: {reg['id']}")

    print("\n4. Simulando atualização de registro...")
    update_success = demo_db.update_registration('demo001', {'total_attendance': 3})
    print(f"   Atualização da Maria Silva: {'✅' if update_success else '❌'}")

    print("\n5. Simulando mudança de status de sincronização...")
    demo_db.update_sync_status('demo002', 'synced')
    demo_db.update_sync_status('demo003', 'error')

    print("\n6. Registros pendentes de sincronização:")
    pending = demo_db.get_pending_sync_registrations()
    for reg in pending:
        print(f"   ⏳ {reg['name']} | ID: {reg['id']}")

    print("\n7. Testando gerenciador de sincronização...")
    sync_manager = SyncManager(
        "https://jtqxscwmjjaandwujsxq.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
    )

    has_internet = sync_manager.check_internet_connection()
    print(f"   Conexão com internet: {'✅ Disponível' if has_internet else '❌ Indisponível'}")

    if has_internet:
        print("   Testando download de dados remotos...")
        remote_data = sync_manager.download_from_supabase()
        print(f"   Registros encontrados no Supabase: {len(remote_data)}")

    print("\n8. Estatísticas finais:")
    final_stats = demo_db.get_database_stats()
    print(f"   Total: {final_stats['total_registrations']}")
    print(f"   Pendentes: {final_stats['pending_sync']}")
    print(f"   Sincronizados: {final_stats['synced']}")
    print(f"   Com erro: {final_stats['error']}")

    print("\n" + "=" * 60)
    print("DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 60)


if __name__ == "__main__":
    print("Executando testes do sistema...")

    # Executar testes unitários
    unittest.main(argv=[''], exit=False, verbosity=2)

    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS - INICIANDO DEMONSTRAÇÃO")
    print("=" * 60)

    # Executar demonstração
    run_demonstration()

