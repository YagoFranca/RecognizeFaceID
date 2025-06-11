import pickle
import cv2
import face_recognition
import cvzone
import numpy as np
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import requests
import os
import sys
from pathlib import Path

# Carrega variáveis de ambiente do .env (se houver)
load_dotenv()


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
            print(f"✅ Recurso encontrado em: {path}")
            return str(path)

    print("\n🚨 DIAGNÓSTICO DE ERRO:")
    print(f"Procurando: {resource_path}")
    print("Locais verificados:")
    for p in project_paths:
        print(f"- {p} → Existe: {p.exists()}")

    raise FileNotFoundError(f"Arquivo não encontrado: {resource_path}")


# Configuração Supabase
SUPABASE_URL = "https://jtqxscwmjjaandwujsxq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    'border': (74, 85, 104)  # Bordas
}


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
        'already_registered': COLORS['info']
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
        'error': COLORS['error']
    }

    banner_color = colors.get(notification_type, COLORS['info'])

    # Banner com gradiente
    draw_gradient_rect(img, (x, y), (x + w, y + h), banner_color,
                       tuple(max(0, c - 30) for c in banner_color))

    # Borda
    cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['text_primary'], 3)

    # Ícone baseado no tipo
    icons = {
        'success': '✓',
        'info': 'ℹ',
        'warning': '⚠',
        'error': '✗'
    }

    icon = icons.get(notification_type, 'ℹ')

    # Desenhar ícone (simulado com formas geométricas)
    if notification_type == 'success':
        # Checkmark verde
        cv2.circle(img, (x + 40, y + h // 2), 20, COLORS['text_primary'], 3)
        # Simular checkmark com linhas
        cv2.line(img, (x + 30, y + h // 2), (x + 38, y + h // 2 + 8), COLORS['text_primary'], 4)
        cv2.line(img, (x + 38, y + h // 2 + 8), (x + 50, y + h // 2 - 8), COLORS['text_primary'], 4)
    elif notification_type == 'info':
        # Círculo info
        cv2.circle(img, (x + 40, y + h // 2), 20, COLORS['text_primary'], 3)
        cv2.putText(img, "i", (x + 35, y + h // 2 + 8), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLORS['text_primary'], 3)

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
    cv2.putText(img, "SISTEMA DE RECONHECIMENTO FACIAL", (40, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLORS['text_primary'], 3)

    # Timestamp
    now = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    cv2.putText(img, now, (width - 300, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_primary'], 2)

    return img


# Inicialização da câmera
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# Carregando encodings de rosto
print("Loading Encode File ...")
try:
    with open(get_resource('EncodeFile.p'), 'rb') as file:
        encodeListKnownWithIds = pickle.load(file)
    encodeListKnown, studentIds = encodeListKnownWithIds
    print("Encode File Loaded")
except FileNotFoundError:
    print("❌ Arquivo de encodings não encontrado!")
    encodeListKnown, studentIds = [], []

# Variáveis de controle
modeType = 0
counter = 0
id = -1
imgStudent = []
no_face_counter = 0
MAX_NO_FACE_FRAMES = 30
studentInfo = {}

# Novas variáveis para controle de notificações
notification_message = ""
notification_type = ""
notification_timer = 0
NOTIFICATION_DURATION = 150  # frames para mostrar a notificação


# Funções auxiliares Supabase (mantidas as mesmas)
def get_student_info(student_id):
    result = supabase.table("FaceAttendenceRealTime").select("*").eq("id", student_id).limit(1).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    else:
        print(f"❌ Nenhum aluno encontrado com id: {student_id}")
        return None


def update_attendance(student_id, total_attendance):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    supabase.table("FaceAttendenceRealTime").update({
        "total_attendance": total_attendance,
        "last_attendance_time": now
    }).eq("id", student_id).execute()


def get_student_image(student_id):
    storage_path = f"{student_id}.png"
    url = supabase.storage.from_("storageforphotos").get_public_url(storage_path)
    if url.endswith('?'):
        url = url[:-1]

    print(f"URL da imagem: {url}")
    resp = requests.get(url)
    if resp.status_code == 200:
        array = np.frombuffer(resp.content, np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            print("❌ Erro: cv2.imdecode retornou None (conteúdo inválido)")
        return image
    else:
        print(f"❌ Erro ao baixar imagem do aluno: HTTP {resp.status_code}")
        return None


def set_notification(message, notif_type="info"):
    """Define uma notificação para ser exibida"""
    global notification_message, notification_type, notification_timer
    notification_message = message
    notification_type = notif_type
    notification_timer = NOTIFICATION_DURATION


def draw_student_info_card(img, x, y, w, h):
    """Desenha o card com informações do usuario"""
    if not studentInfo:
        cv2.putText(img, "Aguardando reconhecimento...", (x + 20, y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['text_secondary'], 2)
        return

    # Nome do usuario
    name = studentInfo.get('name', 'N/A')
    cv2.putText(img, name, (x + 20, y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLORS['text_primary'], 2)

    # ID
    cv2.putText(img, f"ID: {studentInfo.get('id', 'N/A')}", (x + 20, y + 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_secondary'], 2)

    # Grupo
    cv2.putText(img, f"Grupo: {studentInfo.get('group', 'N/A')}", (x + 20, y + 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_secondary'], 2)

    # Frequência
    attendance = studentInfo.get('total_attendance', 0)
    cv2.putText(img, f"Presencas: {attendance}", (x + 20, y + 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['success'], 2)

    # Última presença
    last_attendance = studentInfo.get('last_attendance_time', 'Nunca')
    if last_attendance != 'Nunca':
        try:
            dt = datetime.fromisoformat(last_attendance)
            last_attendance = dt.strftime("%d/%m/%Y %H:%M")
        except:
            pass

    cv2.putText(img, f"Ultima: {last_attendance}", (x + 20, y + 170),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_secondary'], 1)


def draw_camera_feed(img, camera_img, x, y, w, h):
    """Desenha o feed da câmera com moldura moderna"""
    if camera_img is not None:
        # Redimensiona a imagem da câmera
        camera_resized = cv2.resize(camera_img, (w - 20, h - 20))

        # Moldura
        cv2.rectangle(img, (x, y), (x + w, y + h), COLORS['border'], 3)
        cv2.rectangle(img, (x + 5, y + 5), (x + w - 5, y + h - 5), COLORS['primary'], 2)

        # Imagem da câmera
        img[y + 10:y + h - 10, x + 10:x + w - 10] = camera_resized


def is_already_registered_today(student_id):
    """
    Verifica se já foi registrado hoje

    Args:
        student_id: ID

    Returns:
        bool: True se já foi registrado hoje, False caso contrário
    """
    try:
        # Obter a data de hoje no formato YYYY-MM-DD
        today = datetime.now().strftime("%Y-%m-%d")

        # Buscar informações do usuario
        result = supabase.table("FaceAttendenceRealTime").select("last_attendance_time").eq("id", student_id).limit(
            1).execute()

        if result.data and len(result.data) > 0:
            last_attendance_str = result.data[0].get('last_attendance_time')

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
            print(f"Usuario com ID {student_id} não encontrado")
            return False

    except Exception as e:
        print(f"Erro ao verificar registro diário: {e}")
        return False


# Loop principal
print("🚀 Iniciando sistema de reconhecimento facial...")

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

    if faceCurFrame:
        status = "active"
        status_text = f"Rosto detectado ({len(faceCurFrame)})"
        no_face_counter = 0

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

            if len(faceDis) > 0:
                matchIndex = np.argmin(faceDis)
                if matches[matchIndex]:
                    # Desenha retângulo no rosto reconhecido
                    y1, x2, y2, x1 = [val * 4 for val in faceLoc]
                    bbox = x1, y1, x2 - x1, y2 - y1
                    img_resized = cvzone.cornerRect(img_resized, bbox, rt=0,
                                                    colorR=COLORS['success'])

                    id = studentIds[matchIndex]
                    if counter == 0:
                        status = "loading"
                        status_text = "Carregando dados..."
                        counter = 1
                        modeType = 1
    else:
        no_face_counter += 1
        if no_face_counter > MAX_NO_FACE_FRAMES:
            modeType = 0
            counter = 0
            studentInfo = {}
            imgStudent = []

    # Processa reconhecimento
    if counter != 0:
        if counter == 1:
            studentInfo = get_student_info(id)
            if studentInfo is None:
                counter = 0
                modeType = 0
                continue

            imgStudent = get_student_image(id)

            # Verifica se já foi registrado hoje
            if is_already_registered_today(id):
                status = "already_registered"
                status_text = f"Já registrado hoje: {studentInfo['name']}"
                set_notification(f"{studentInfo['name']} - JA REGISTRADO HOJE!", "info")
                print(f"🔄 Usuario {studentInfo['name']} já registrado hoje - não contabilizando")
            else:
                # Registra a presença
                update_attendance(id, studentInfo['total_attendance'] + 1)
                studentInfo['total_attendance'] += 1
                status = "new_registration"
                status_text = f"Nova presença: {studentInfo['name']}"
                set_notification(f"NOVO REGISTRO! {studentInfo['name']} - Presenca #{studentInfo['total_attendance']}",
                                 "success")
                print(f"✅ Nova presença registrada para {studentInfo['name']}")

        counter += 1
        if counter >= 100:  # Reset após um tempo
            counter = 0
            modeType = 0
            studentInfo = {}
            imgStudent = []

    # Desenha os componentes da interface

    # Notificação grande (se ativa)
    if notification_timer > 0:
        draw_notification_banner(interface, 40, 90, 1200, 80,
                                 notification_message, notification_type)
        notification_timer -= 1

        # Ajusta posição dos outros elementos quando há notificação
        camera_y = 180
        info_y = 180
        student_photo_y = 500
        metrics_y = 500
        status_y = 660
    else:
        # Posições normais quando não há notificação
        camera_y = 100
        info_y = 100
        student_photo_y = 420
        metrics_y = 420
        status_y = 580

    # Feed da câmera (lado esquerdo)
    draw_modern_card(interface, 40, camera_y, 660, 400, "Camera ao vivo")
    draw_camera_feed(interface, img_resized, 60, camera_y + 60, 620, 320)

    # Status do sistema
    draw_status_indicator(interface, 60, status_y, status, status_text)

    # Card de informações do usuario (lado direito)
    draw_modern_card(interface, 720, info_y, 520, 300, "Detalhes do Usuario",
                     draw_student_info_card)

    # Foto do usuario
    if imgStudent is not None and len(imgStudent) > 0:
        draw_modern_card(interface, 720, student_photo_y, 250, 270, "FOTO")
        try:
            # Redimensiona a imagem do usuario
            student_resized = cv2.resize(imgStudent, (210, 200))

            # Calcula as posições corretas considerando o padding do card
            start_y = student_photo_y + 60  # 50 para o header + 10 de padding
            end_y = start_y + 200
            start_x = 740  # 720 + 20 de padding
            end_x = start_x + 210

            # Verifica se as dimensões estão dentro dos limites da interface
            if end_y <= interface.shape[0] and end_x <= interface.shape[1]:
                interface[start_y:end_y, start_x:end_x] = student_resized
            else:
                print(f"Dimensões da foto excedem os limites da interface")

        except Exception as e:
            print(f"Erro ao exibir foto do usuario: {e}")

    # Métricas (cards pequenos)
    total_students = len(studentIds)
    total_attendance = studentInfo.get('total_attendance', 0) if studentInfo else 0
    draw_metric_card(interface, 990, metrics_y, 120, 100, total_students, "CADASTRADOS")
    draw_metric_card(interface, 1120, metrics_y, 120, 100,studentInfo.get('total_attendance', 0), "PRESENCAS")

    # Footer
    footer_y = 760 if notification_timer == 0 else 840
    if footer_y < interface.shape[0]:
        cv2.line(interface, (0, footer_y), (1280, footer_y), COLORS['border'], 2)
        cv2.putText(interface, "Sistema Desenvolvido para Controle de Presenca",
                    (40, footer_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_secondary'], 1)

        # Instruções
        cv2.putText(interface, "Pressione 'q' para sair | 'r' para resetar",
                    (900, footer_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_secondary'], 1)

    # Exibe a interface
    cv2.imshow("Sistema de Reconhecimento Facial", interface)

    # Controles do teclado
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        counter = 0
        modeType = 0
        studentInfo = {}
        imgStudent = []
        notification_timer = 0  # Reset da notificação também
        print("🔄 Sistema resetado")

    # Verifica se a janela foi fechada
    if cv2.getWindowProperty("Sistema de Reconhecimento Facial", cv2.WND_PROP_VISIBLE) < 1:
        print("Janela fechada pelo usuário.")
        break

# Limpeza
cap.release()
cv2.destroyAllWindows()
print("👋 Sistema encerrado com sucesso!")