"""
Sistema de Reconhecimento Facial Integrado com Banco Local
Versão Melhorada com Maior Precisão e Controle de Falsos Positivos
Autor: Sistema de Reconhecimento Facial
"""

import pickle
import cv2
import face_recognition
import cvzone
import numpy as np
from datetime import datetime
import requests
import os
import sys
from pathlib import Path
import threading
import time
import tkinter as tk

# Importar módulos do sistema offline
from local_database import LocalDatabase, serialize_encoding, deserialize_encoding
from sync_manager import create_sync_manager_from_config


# CONFIGURAÇÕES DE PRECISÃO MELHORADAS
class RecognitionConfig:
    # Threshold mais restritivo para reduzir falsos positivos
    FACE_DISTANCE_THRESHOLD = 0.45  # Reduzido de 0.6 padrão para 0.45

    # Threshold de confiança mínima
    MIN_CONFIDENCE_THRESHOLD = 0.55  # 55% de confiança mínima

    # Número de frames consecutivos para confirmar reconhecimento
    CONFIRMATION_FRAMES = 5  # Precisa reconhecer por 5 frames seguidos

    # Tamanho mínimo da face para processar (evita faces muito pequenas/distantes)
    MIN_FACE_SIZE = 50  # pixels

    # Número máximo de faces para processar simultaneamente
    MAX_FACES_TO_PROCESS = 3

    # Tempo mínimo entre reconhecimentos da mesma pessoa (segundos)
    MIN_TIME_BETWEEN_SAME_PERSON = 3


# Função para resolução de caminhos (compatível com PyInstaller)
def get_resource(resource_path):
    """Resolve caminhos considerando a nova estrutura de diretórios"""
    project_root = Path(__file__).parent.parent
    project_paths = [
        project_root / resource_path,
        project_root / "ProjetoD" / resource_path
    ]

    if hasattr(sys, '_MEIPASS'):
        meipass_path = Path(sys._MEIPASS) / resource_path
        project_paths.insert(0, meipass_path)

    project_paths.extend([
        Path(resource_path).absolute(),
        Path.cwd() / resource_path,
        Path(sys.executable).parent / resource_path
    ])

    for path in project_paths:
        if path.exists():
            print(f"Recurso encontrado em: {path}")
            return str(path)

    print("\n🚨 DIAGNÓSTICO DE ERRO:")
    print(f"Procurando: {resource_path}")
    print("Locais verificados:")
    for p in project_paths:
        print(f"- {p} → Existe: {p.exists()}")

    raise FileNotFoundError(f"Arquivo não encontrado: {resource_path}")


# Configurações de cores e design moderno
COLORS = {
    'primary': (32, 201, 151),  # Verde moderno
    'secondary': (45, 55, 72),  # Cinza escuro
    'accent': (66, 153, 225),  # Azul
    'success': (72, 187, 120),  # Verde sucesso
    'warning': (237, 137, 54),  # Laranja
    'error': (245, 101, 101),  # Vermelho
    'info': (56, 178, 172),  # Azul claro
    'background': (26, 32, 44),  # Fundo escuro
    'surface': (45, 55, 72),  # Superfície
    'text_primary': (255, 255, 255),  # Texto principal
    'text_secondary': (160, 174, 192),  # Texto secundário
    'border': (74, 85, 104),  # Bordas
    'unknown': (255, 165, 0),  # Laranja para pessoa desconhecida
    'low_confidence': (255, 255, 0)  # Amarelo para baixa confiança
}

def on_close():
    print("Janela será fechada!")
    root.destroy()

def draw_gradient_rect(img, pt1, pt2, color1, color2, vertical=True):
    """Desenha um retângulo com gradiente"""
    x1, y1 = pt1
    x2, y2 = pt2

    if vertical:
        for i in range(y1, y2):
            ratio = (i - y1) / (y2 - y1)
            color = tuple(int(c1 + (c2 - c1) * ratio) for c1, c2 in zip(color1, color2))
            cv2.line(img, (x1, i), (x2, i), color, 1)
    else:
        for i in range(x1, x2):
            ratio = (i - x1) / (x2 - x1)
            color = tuple(int(c1 + (c2 - c1) * ratio) for c1, c2 in zip(color1, color2))
            cv2.line(img, (i, y1), (i, y2), color, 1)


def draw_modern_card(img, x, y, w, h, title="", content_func=None):
    """Desenha um card moderno com sombra e bordas arredondadas"""
    # Sombra
    shadow_offset = 8
    cv2.rectangle(img, (x + shadow_offset, y + shadow_offset),
                  (x + w + shadow_offset, y + h + shadow_offset),
                  (0, 0, 0), -1)

    # Card principal
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['surface'], -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['border'], 2)

    # Header do card se houver título
    if title:
        header_height = 50
        draw_gradient_rect(img, (x, y), (x + w, y + header_height),
                           COLORS['primary'], COLORS['accent'])
        cv2.putText(img, title, (x + 20, y + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['text_primary'], 2)

        if content_func:
            content_func(img, x, y + header_height, w, h - header_height)
    elif content_func:
        content_func(img, x, y, w, h)


def draw_status_indicator(img, x, y, status, text):
    """Desenha um indicador de status moderno"""
    colors = {
        'active': COLORS['success'],
        'loading': COLORS['warning'],
        'error': COLORS['error'],
        'idle': COLORS['text_secondary'],
        'new_registration': COLORS['success'],
        'already_registered': COLORS['info'],
        'offline': COLORS['warning'],
        'online': COLORS['success'],
        'unknown_person': COLORS['unknown'],
        'low_confidence': COLORS['low_confidence'],
        'confirming': COLORS['accent']
    }

    color = colors.get(status, COLORS['text_secondary'])

    # Círculo indicador
    cv2.circle(img, (x + 10, y + 15), 8, color, -1)
    cv2.circle(img, (x + 10, y + 15), 8, COLORS['text_primary'], 2)

    # Texto do status
    cv2.putText(img, text, (x + 30, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_primary'], 2)


def draw_notification_banner(img, x, y, w, h, message, notification_type="info"):
    """Desenha um banner de notificação grande e chamativo"""
    colors = {
        'success': COLORS['success'],
        'info': COLORS['info'],
        'warning': COLORS['warning'],
        'error': COLORS['error'],
        'unknown': COLORS['unknown']
    }

    banner_color = colors.get(notification_type, COLORS['info'])

    # Banner com gradiente
    draw_gradient_rect(img, (x, y), (x + w, y + h), banner_color,
                       tuple(max(0, c - 30) for c in banner_color))

    # Borda
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['text_primary'], 3)

    # Ícone baseado no tipo
    if notification_type == 'success':
        # Checkmark verde
        cv2.circle(img, (x + 40, y + h // 2), 20, COLORS['text_primary'], 3)
        cv2.line(img, (x + 30, y + h // 2), (x + 38, y + h // 2 + 8), COLORS['text_primary'], 4)
        cv2.line(img, (x + 38, y + h // 2 + 8), (x + 50, y + h // 2 - 8), COLORS['text_primary'], 4)
    elif notification_type == 'unknown':
        # Ponto de interrogação para pessoa desconhecida
        cv2.circle(img, (x + 40, y + h // 2), 25, COLORS['text_primary'], 4)
        cv2.putText(img, "?", (x + 33, y + h // 2 + 9), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLORS['text_primary'], 3)
    elif notification_type == 'info':
        # Círculo info
        cv2.circle(img, (x + 40, y + h // 2), 25, COLORS['text_primary'], 4)
        cv2.putText(img, "i", (x + 35, y + h // 2 + 9), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLORS['text_primary'], 3)

    # Texto da mensagem
    cv2.putText(img, message, (x + 80, y + h // 2 + 8),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLORS['text_primary'], 2)


def draw_metric_card(img, x, y, w, h, value, label, icon=""):
    """Desenha um card de métrica"""
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['surface'], -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['border'], 2)

    # Valor principal
    cv2.putText(img, str(value), (x + 20, y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, COLORS['primary'], 3)

    # Label
    cv2.putText(img, label, (x + 20, y + h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_secondary'], 1)


def create_modern_interface(width=1280, height=800):
    """Cria a interface moderna"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = COLORS['background']

    # Header
    draw_gradient_rect(img, (0, 0), (width, 80), COLORS['primary'], COLORS['accent'])
    cv2.putText(img, "SISTEMA DE RECONHECIMENTO FACIAL - PRECISAO MELHORADA", (45, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORS['text_primary'], 3)

    # Timestamp
    now = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    cv2.putText(img, now, (width - 300, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_primary'], 2)

    return img


class OfflineFaceRecognitionSystem:
    """Sistema de reconhecimento facial offline-first com precisão melhorada"""

    def __init__(self):
        # Inicializar banco local e sincronização
        self.local_db = LocalDatabase()
        self.sync_manager = create_sync_manager_from_config()

        # Carregar encodings do banco local
        self.load_encodings_from_database()

        # Variáveis de controle melhoradas
        self.modeType = 0
        self.counter = 0
        self.id = -1
        self.imgStudent = []
        self.no_face_counter = 0
        self.MAX_NO_FACE_FRAMES = 30
        self.studentInfo = {}

        # Variáveis para controle de notificações
        self.notification_message = ""
        self.notification_type = ""
        self.notification_timer = 0
        self.NOTIFICATION_DURATION = 150

        # Status de conexão
        self.has_internet = False
        self.last_sync_check = 0

        # Variáveis para controle de precisão
        self.recognition_history = {}  # Histórico de reconhecimentos por ID
        self.confirmation_counter = {}  # Contador de confirmações por pessoa
        self.last_recognition_time = {}  # Último tempo de reconhecimento por pessoa
        self.current_recognition_confidence = 0.0
        self.unknown_face_counter = 0

        # Configuração
        self.config = RecognitionConfig()

        # Iniciar sincronização automática
        self.auto_sync_enabled = True
        self.start_auto_sync()

        print("Sistema de reconhecimento facial melhorado iniciado!")
        print(f"Configuracoes de precisao:")
        print(f"   - Threshold de distância: {self.config.FACE_DISTANCE_THRESHOLD}")
        print(f"   - Confiança mínima: {self.config.MIN_CONFIDENCE_THRESHOLD}")
        print(f"   - Frames de confirmação: {self.config.CONFIRMATION_FRAMES}")

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

            print(f"Carregados {len(self.encodeListKnown)} encodings do banco local")

        except Exception as e:
            print(f"Erro ao carregar encodings: {e}")
            self.encodeListKnown, self.studentIds = [], []

    def calculate_face_confidence(self, face_distance):
        """Calcula a confiança do reconhecimento baseado na distância"""
        if face_distance > self.config.FACE_DISTANCE_THRESHOLD:
            return 0.0

        # Converte distância em porcentagem de confiança
        confidence = (1 - face_distance) * 100
        return max(0, min(100, confidence))

    def is_face_size_adequate(self, face_location):
        """Verifica se o tamanho da face é adequado para reconhecimento"""
        top, right, bottom, left = face_location
        face_width = right - left
        face_height = bottom - top

        return (face_width >= self.config.MIN_FACE_SIZE and
                face_height >= self.config.MIN_FACE_SIZE)

    def should_process_recognition(self, student_id):
        """Verifica se deve processar o reconhecimento baseado no tempo"""
        current_time = time.time()

        if student_id in self.last_recognition_time:
            time_diff = current_time - self.last_recognition_time[student_id]
            if time_diff < self.config.MIN_TIME_BETWEEN_SAME_PERSON:
                return False

        return True

    def update_confirmation_counter(self, student_id):
        """Atualiza contador de confirmação para uma pessoa"""
        if student_id not in self.confirmation_counter:
            self.confirmation_counter[student_id] = 0

        self.confirmation_counter[student_id] += 1

        # Limpar contadores de outras pessoas
        for other_id in list(self.confirmation_counter.keys()):
            if other_id != student_id:
                self.confirmation_counter[other_id] = 0

    def is_recognition_confirmed(self, student_id):
        """Verifica se o reconhecimento foi confirmado por frames suficientes"""
        return (student_id in self.confirmation_counter and
                self.confirmation_counter[student_id] >= self.config.CONFIRMATION_FRAMES)

    def reset_recognition_state(self):
        """Reseta o estado de reconhecimento"""
        self.confirmation_counter.clear()
        self.modeType = 0
        self.counter = 0
        self.studentInfo = {}
        self.imgStudent = []
        self.current_recognition_confidence = 0.0
        self.unknown_face_counter = 0

    def start_auto_sync(self):
        """Inicia sincronização automática em background"""
        def auto_sync_worker():
            while self.auto_sync_enabled:
                try:
                    # Verificar conexão
                    self.has_internet = self.sync_manager.check_internet_connection()

                    if self.has_internet:
                        # Fazer sincronização automática a cada 60 segundos
                        result = self.sync_manager.full_sync()

                        # Se houve downloads, recarregar encodings
                        if result.get('downloads', 0) > 0:
                            self.load_encodings_from_database()
                            print(f"Encodings recarregados apos sincronizacao")

                    # Aguardar 60 segundos antes da próxima verificação
                    time.sleep(60)

                except Exception as e:
                    print(f"Erro na sincronização automática: {e}")
                    time.sleep(60)

        # Iniciar thread de sincronização
        sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
        sync_thread.start()

    def get_student_info_local(self, student_id):
        """Busca informações do estudante no banco local"""
        try:
            registro = self.local_db.get_registration(student_id)
            if registro:
                # Converter formato do banco local para formato esperado
                return {
                    'id': registro['id'],
                    'name': registro['name'],
                    'group': registro['group_name'],
                    'phone': registro['phone'],
                    'event': registro.get('event'),
                    'total_attendance': registro['total_attendance'],
                    'last_attendance_time': registro.get('last_attendance_time')
                }
            else:
                print(f"Nenhum usuario encontrado com id: {student_id}")
                return None
        except Exception as e:
            print(f"Erro ao buscar informacoes do usuario: {e}")
            return None

    def update_attendance_local(self, student_id, total_attendance):
        """Atualiza presença no banco local"""
        try:
            now = datetime.now().isoformat()
            update_data = {
                'total_attendance': total_attendance,
                'last_attendance_time': now
            }

            success = self.local_db.update_registration(student_id, update_data)
            if success:
                print(f"Presenca atualizada localmente para {student_id}")
                # Atualizar tempo da última reconfiguração
                self.last_recognition_time[student_id] = time.time()
            else:
                print(f"Erro ao atualizar presenca para {student_id}")

            return success

        except Exception as e:
            print(f"Erro ao atualizar presenca: {e}")
            return False

    def get_student_image_local(self, student_id):
        """Busca imagem do estudante localmente"""
        try:
            registro = self.local_db.get_registration(student_id)
            if registro and registro.get('image_path'):
                image_path = registro['image_path']

                # Verificar se arquivo existe localmente
                if os.path.exists(image_path):
                    image = cv2.imread(image_path)
                    if image is not None:
                        print(f"Imagem carregada localmente: {image_path}")
                        return image
                    else:
                        print(f"Erro ao carregar imagem: {image_path}")
                else:
                    print(f"Arquivo de imagem nao encontrado: {image_path}")

            # Se não encontrou localmente e há internet, tentar baixar
            if self.has_internet:
                print(f"Tentando baixar imagem do storage para {student_id}")
                return self.download_student_image(student_id)

            return None

        except Exception as e:
            print(f"Erro ao buscar imagem: {e}")
            return None

    def download_student_image(self, student_id):
        """Baixa imagem do Supabase Storage"""
        try:
            # Usar a URL do Supabase Storage
            storage_path = f"{student_id}.png"
            url = f"https://jtqxscwmjjaandwujsxq.supabase.co/storage/v1/object/public/storageforphotos/{storage_path}"

            print(f"URL da imagem: {url}")
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                array = np.frombuffer(resp.content, np.uint8)
                image = cv2.imdecode(array, cv2.IMREAD_COLOR)

                if image is not None:
                    # Salvar localmente para uso futuro
                    os.makedirs("Images", exist_ok=True)
                    local_path = f"Images/{student_id}.png"
                    cv2.imwrite(local_path, image)

                    # Atualizar caminho no banco local
                    self.local_db.update_registration(student_id, {'image_path': local_path})

                    print(f"Imagem baixada e salva: {local_path}")
                    return image
                else:
                    print("Erro: cv2.imdecode retornou None")
            else:
                print(f"Erro ao baixar imagem: HTTP {resp.status_code}")

            return None

        except Exception as e:
            print(f"Erro ao baixar imagem: {e}")
            return None

    def is_already_registered_today_local(self, student_id):
        """Verifica se já foi registrado hoje no banco local"""
        try:
            # Obter a data de hoje no formato YYYY-MM-DD
            today = datetime.now().strftime("%Y-%m-%d")

            # Buscar informações do usuário no banco local
            registro = self.local_db.get_registration(student_id)

            if registro:
                last_attendance_str = registro.get('last_attendance_time')

                if last_attendance_str:
                    try:
                        # Converter string para datetime
                        last_attendance = datetime.fromisoformat(last_attendance_str)
                        last_attendance_date = last_attendance.strftime("%Y-%m-%d")

                        # Verificar se a última presença foi hoje
                        return last_attendance_date == today

                    except Exception as e:
                        print(f"Erro ao processar data da última presença: {e}")
                        return False
                else:
                    # Se não há registro de última presença, não foi registrado hoje
                    return False
            else:
                print(f"Usuário com ID {student_id} não encontrado no banco local")
                return False

        except Exception as e:
            print(f"Erro ao verificar registro diário: {e}")
            return False

    def set_notification(self, message, notif_type="info"):
        """Define uma notificação para ser exibida"""
        self.notification_message = message
        self.notification_type = notif_type
        self.notification_timer = self.NOTIFICATION_DURATION

    def draw_student_info_card(self, img, x, y, w, h):
        """Desenha o card com informações do usuário"""
        if not self.studentInfo:
            cv2.putText(img, "Aguardando reconhecimento...", (x + 20, y + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['text_secondary'], 2)
            return

        # Nome do usuário
        name = self.studentInfo.get('name', 'N/A')
        cv2.putText(img, name, (x + 20, y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLORS['text_primary'], 2)

        # ID
        cv2.putText(img, f"ID: {self.studentInfo.get('id', 'N/A')}", (x + 20, y + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_secondary'], 2)

        # Confiança do reconhecimento
        confidence_text = f"Confianca: {self.current_recognition_confidence:.1f}%"
        confidence_color = COLORS['success'] if self.current_recognition_confidence >= 70 else COLORS['warning']
        cv2.putText(img, confidence_text, (x + 20, y + 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, confidence_color, 2)

        # Grupo
        cv2.putText(img, f"Grupo: {self.studentInfo.get('group', 'N/A')}", (x + 20, y + 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_secondary'], 2)

        # Frequência
        attendance = self.studentInfo.get('total_attendance', 0)
        cv2.putText(img, f"Presencas: {attendance}", (x + 20, y + 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['success'], 2)

        # Última presença
        last_attendance = self.studentInfo.get('last_attendance_time', 'Nunca')
        if last_attendance != 'Nunca':
            try:
                dt = datetime.fromisoformat(last_attendance)
                last_attendance = dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass

        cv2.putText(img, f"Ultima: {last_attendance}", (x + 20, y + 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_secondary'], 1)

    def draw_camera_feed(self, img, camera_img, x, y, w, h):
        """Desenha o feed da câmera com moldura moderna"""
        if camera_img is not None:
            # Redimensiona a imagem da câmera
            camera_resized = cv2.resize(camera_img, (w - 20, h - 20))

            # Moldura
            cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['border'], 3)
            cv2.rectangle(img, (x + 5, y + 5), (x + w - 5, y + h - 5), COLORS['primary'], 2)

            # Imagem da câmera
            img[y + 10:y + h - 10, x + 10:x + w - 10] = camera_resized

    def run(self):
        """Executa o loop principal do sistema"""
        # Inicialização da câmera
        cap = cv2.VideoCapture(0)
        cap.set(3, 640)
        cap.set(4, 480)

        print("Iniciando sistema de reconhecimento facial...")

        while True:
            success, img = cap.read()
            if not success:
                print("Falha ao capturar frame da câmera")
                break

            # Cria a interface moderna
            interface = create_modern_interface()

            # Processa imagem para reconhecimento
            img_resized = cv2.resize(img, (640, 480))
            imgS = cv2.resize(img_resized, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            # Detecta rostos e codifica
            faceCurFrame = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

            # Status do sistema
            status = "idle"
            status_text = "Aguardando..."

            # Indicador de conexão
            connection_status = "online" if self.has_internet else "offline"
            connection_text = "Online" if self.has_internet else "Offline"

            # Limitar número de faces processadas
            if len(faceCurFrame) > self.config.MAX_FACES_TO_PROCESS:
                faceCurFrame = faceCurFrame[:self.config.MAX_FACES_TO_PROCESS]
                encodeCurFrame = encodeCurFrame[:self.config.MAX_FACES_TO_PROCESS]

            if faceCurFrame and len(self.encodeListKnown) > 0:
                status = "active"
                status_text = f"Analisando {len(faceCurFrame)} rosto(s)..."
                self.no_face_counter = 0

                best_match_id = None
                best_confidence = 0
                best_face_loc = None

                for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                    # Verificar tamanho adequado da face
                    if not self.is_face_size_adequate(faceLoc):
                        continue

                    # Calcular distâncias para todas as faces conhecidas
                    face_distances = face_recognition.face_distance(self.encodeListKnown, encodeFace)
                    matches = face_recognition.compare_faces(self.encodeListKnown, encodeFace,
                                                           tolerance=self.config.FACE_DISTANCE_THRESHOLD)

                    if len(face_distances) > 0:
                        min_distance_index = np.argmin(face_distances)
                        min_distance = face_distances[min_distance_index]

                        # Calcular confiança
                        confidence = self.calculate_face_confidence(min_distance)

                        print(f"Distancia minima: {min_distance:.3f}, Confianca: {confidence:.1f}%")

                        # Verificar se passou nos thresholds
                        if (matches[min_distance_index] and
                            confidence >= self.config.MIN_CONFIDENCE_THRESHOLD and
                            min_distance <= self.config.FACE_DISTANCE_THRESHOLD):

                            potential_id = self.studentIds[min_distance_index]

                            # Verificar se é a melhor correspondência até agora
                            if confidence > best_confidence:
                                best_match_id = potential_id
                                best_confidence = confidence
                                best_face_loc = faceLoc

                        else:
                            # Face desconhecida ou confiança baixa
                            y1, x2, y2, x1 = [val * 4 for val in faceLoc]
                            bbox = x1, y1, x2 - x1, y2 - y1

                            if confidence < self.config.MIN_CONFIDENCE_THRESHOLD:
                                # Baixa confiança - amarelo
                                img_resized = cvzone.cornerRect(img_resized, bbox, rt=0,
                                                              colorR=COLORS['low_confidence'])
                                cv2.putText(img_resized, f"Baixa Conf: {confidence:.1f}%",
                                          (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                          COLORS['low_confidence'], 2)
                                status = "low_confidence"
                                status_text = f"Baixa confiança: {confidence:.1f}%"
                            else:
                                # Pessoa desconhecida - laranja
                                img_resized = cvzone.cornerRect(img_resized, bbox, rt=0,
                                                              colorR=COLORS['unknown'])
                                cv2.putText(img_resized, "DESCONHECIDO",
                                          (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                          COLORS['unknown'], 2)

                                self.unknown_face_counter += 1
                                if self.unknown_face_counter > 30:  # 1 segundo a 30fps
                                    status = "unknown_person"
                                    status_text = "Pessoa desconhecida detectada"
                                    self.set_notification("PESSOA DESCONHECIDA DETECTADA!", "unknown")
                                    self.unknown_face_counter = 0

                # Processar melhor correspondência
                if best_match_id is not None:
                    self.current_recognition_confidence = best_confidence

                    # Desenhar retângulo verde na melhor correspondência
                    y1, x2, y2, x1 = [val * 4 for val in best_face_loc]
                    bbox = x1, y1, x2 - x1, y2 - y1
                    img_resized = cvzone.cornerRect(img_resized, bbox, rt=0,
                                                  colorR=COLORS['success'])

                    # Mostrar confiança no retângulo
                    cv2.putText(img_resized, f"{best_confidence:.1f}%",
                              (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                              COLORS['success'], 2)

                    # Atualizar contador de confirmação
                    self.update_confirmation_counter(best_match_id)

                    # Verificar se precisa de mais confirmações
                    if not self.is_recognition_confirmed(best_match_id):
                        confirmations_needed = (self.config.CONFIRMATION_FRAMES -
                                              self.confirmation_counter.get(best_match_id, 0))
                        status = "confirming"
                        status_text = f"Confirmando... ({confirmations_needed} frames restantes)"
                    else:
                        # Reconhecimento confirmado
                        if self.should_process_recognition(best_match_id):
                            self.id = best_match_id
                            if self.counter == 0:
                                status = "loading"
                                status_text = "Carregando dados..."
                                self.counter = 1
                                self.modeType = 1
                        else:
                            status = "already_registered"
                            status_text = f"Aguardando cooldown para {best_match_id}"
                else:
                    # Limpar contadores se não há correspondência válida
                    self.confirmation_counter.clear()
                    self.unknown_face_counter += 1

            else:
                # Sem faces detectadas
                self.no_face_counter += 1
                self.unknown_face_counter = 0
                if self.no_face_counter > self.MAX_NO_FACE_FRAMES:
                    self.reset_recognition_state()

            # Processa reconhecimento confirmado
            if self.counter != 0:
                if self.counter == 1:
                    self.studentInfo = self.get_student_info_local(self.id)
                    if self.studentInfo is None:
                        self.reset_recognition_state()
                        continue

                    self.imgStudent = self.get_student_image_local(self.id)

                    # Verifica se já foi registrado hoje
                    if self.is_already_registered_today_local(self.id):
                        status = "already_registered"
                        status_text = f"Já registrado hoje: {self.studentInfo['name']}"
                        self.set_notification(f"{self.studentInfo['name']} - JA REGISTRADO HOJE!", "info")
                        print(f"Usuario {self.studentInfo['name']} ja registrado hoje - nao incrementando presenca")
                    else:
                        # Incrementar presença
                        new_attendance = self.studentInfo['total_attendance'] + 1

                        if self.update_attendance_local(self.id, new_attendance):
                            self.studentInfo['total_attendance'] = new_attendance
                            status = "new_registration"
                            status_text = f"Nova presença: {self.studentInfo['name']} ({self.current_recognition_confidence:.1f}%)"
                            self.set_notification(f"{self.studentInfo['name']} - PRESENCA REGISTRADA! ({self.current_recognition_confidence:.1f}%)", "success")
                            print(f"Nova presenca registrada para {self.studentInfo['name']} com {self.current_recognition_confidence:.1f}% de confianca")
                        else:
                            status = "error"
                            status_text = "Erro ao registrar presença"
                            self.set_notification("ERRO AO REGISTRAR PRESENCA!", "error")

                if self.counter <= 60:  # Aumentado para mostrar informações por mais tempo
                    self.counter += 1
                else:
                    self.reset_recognition_state()

            # Desenhar interface
            # Status do sistema
            draw_status_indicator(interface, 50, 100, status, status_text)

            # Status de conexão
            draw_status_indicator(interface, 50, 130, connection_status, f"Conexao: {connection_text}")

            # Status de precisão
            precision_text = f"Threshold: {self.config.FACE_DISTANCE_THRESHOLD} | Min Conf: {self.config.MIN_CONFIDENCE_THRESHOLD}%"
            draw_status_indicator(interface, 50, 160, "info", precision_text)

            # Card de informações do usuário
            draw_modern_card(interface, 50, 200, 420, 250, "Informacoes do Usuario", self.draw_student_info_card)

            # Feed da câmera
            self.draw_camera_feed(interface, img_resized, 500, 100, 640, 480)

            # Imagem do usuário (se disponível)
            if self.imgStudent is not None and len(self.imgStudent) > 0:
                try:
                    y = 270  # Ajustado para nova posição
                    x = 300

                    imgStudent_resized = cv2.resize(self.imgStudent, (130, 130))
                    interface[y:y+130, x:x+130] = imgStudent_resized

                    # Moldura na imagem do usuário
                    cv2.rectangle(interface, (x-2, y-2), (x+132, y+132), COLORS['primary'], 2)
                except:
                    pass

            # Notificação (se ativa)
            if self.notification_timer > 0:
                draw_notification_banner(interface, 50, 680, 900, 80,
                                       self.notification_message, self.notification_type)
                self.notification_timer -= 1

            # Estatísticas do banco local
            stats = self.local_db.get_database_stats()
            draw_metric_card(interface, 50, 470, 180, 100, stats['total_registrations'], "Registros Locais")
            draw_metric_card(interface, 250, 470, 180, 100, stats['pending_sync'], "Pendentes Sync")

            # Métricas de precisão
            total_confirmations = sum(self.confirmation_counter.values())
            draw_metric_card(interface, 50, 590, 180, 80, f"{self.current_recognition_confidence:.1f}%", "Confianca Atual")
            draw_metric_card(interface, 250, 590, 180, 80, total_confirmations, "Confirmacoes")

            cv2.imshow("Sistema de Reconhecimento Facial - Melhorado", interface)

            # Controles de teclado
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Sincronização manual
                if self.has_internet:
                    print("Iniciando sincronizacao manual...")
                    result = self.sync_manager.full_sync()
                    if result.get('downloads', 0) > 0:
                        self.load_encodings_from_database()
                    print(f"Sincronizacao concluida: {result}")
                else:
                    print("Sem conexao com internet para sincronizacao")
            elif key == ord('r'):
                # Recarregar encodings
                print("Recarregando encodings do banco local...")
                self.load_encodings_from_database()
                self.reset_recognition_state()
            elif key == ord('c'):
                # Limpar estado de reconhecimento
                print("Limpando estado de reconhecimento...")
                self.reset_recognition_state()
            elif key == ord('t'):
                # Ajustar threshold (para testes)
                if self.config.FACE_DISTANCE_THRESHOLD == 0.45:
                    self.config.FACE_DISTANCE_THRESHOLD = 0.4
                    print("Threshold mais restritivo: 0.4")
                elif self.config.FACE_DISTANCE_THRESHOLD == 0.4:
                    self.config.FACE_DISTANCE_THRESHOLD = 0.5
                    print("Threshold mais permissivo: 0.5")
                else:
                    self.config.FACE_DISTANCE_THRESHOLD = 0.45
                    print("Threshold padrao: 0.45")

        # Limpeza
        self.auto_sync_enabled = False
        cap.release()
        cv2.destroyAllWindows()


def main():
    """Função principal"""
    try:
        print("=" * 60)
        print("SISTEMA DE RECONHECIMENTO FACIAL MELHORADO")
        print("=" * 60)
        print("Melhorias implementadas:")
        print("   - Threshold de distancia mais restritivo (0.45)")
        print("   - Verificacao de confianca minima (55%)")
        print("   - Confirmacao por multiplos frames (5 frames)")
        print("   - Deteccao de pessoas desconhecidas")
        print("   - Verificacao de tamanho minimo da face")
        print("   - Cooldown entre reconhecimentos")
        print("   - Indicadores visuais de confianca")
        print("=" * 60)
        print("Controles:")
        print("   - Q: Sair")
        print("   - S: Sincronizacao manual")
        print("   - R: Recarregar encodings")
        print("   - C: Limpar estado de reconhecimento")
        print("   - T: Ajustar threshold de precisao")
        print("=" * 60)

        system = OfflineFaceRecognitionSystem()
        system.run()
    except KeyboardInterrupt:
        print("\nSistema encerrado pelo usuario")
    except Exception as e:
        print(f"Erro no sistema: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()