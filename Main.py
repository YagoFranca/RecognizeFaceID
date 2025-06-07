import os
import pickle
import cv2
import face_recognition
import cvzone
import numpy as np
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import requests
import tkinter as tk
import sys
import os
from pathlib import Path

# Cria a janela principal
root = tk.Tk()
root.focus_set()

# Carrega variáveis de ambiente do .env (se tiver)
load_dotenv()

# Configurações Supabase
SUPABASE_URL = "https://jtqxscwmjjaandwujsxq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

cap = cv2.VideoCapture(0)
cap.set(3, 640)  # Largura
cap.set(4, 480)  # Altura

# Imagem de background e modos
imgBackground = cv2.imread('Resources/background.png')
folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

# Carregando encodings de rosto
print("Loading Encode File ...")
with open('EncodeFile.p', 'rb') as file:
    encodeListKnownWithIds = pickle.load(file)
encodeListKnown, studentIds = encodeListKnownWithIds
print("Encode File Loaded")

modeType = 0
counter = 0
id = -1
imgStudent = []

import sys
import os
from pathlib import Path


def get_resource(resource_path):
    """Resolve caminhos em desenvolvimento e no executável"""
    # PyInstaller cria temp folder em _MEIPASS
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    # Caminhos alternativos para verificação
    search_paths = [
        base_path / resource_path,
        Path.cwd() / resource_path,
        Path(sys.executable).parent / resource_path
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    # Lista arquivos para diagnóstico
    print("\nDIAGNÓSTICO:")
    print(f"Procurando: {resource_path}")
    print("Locais verificados:")
    for p in search_paths:
        print(f"- {p} → Existe: {p.exists()}")

    raise FileNotFoundError(f"Arquivo não encontrado: {resource_path}")


# USO:
try:
    modes_path = get_resource('Resources/Modes')
    print(f"Pasta Modes encontrada em: {modes_path}")
    print(f"Arquivos encontrados: {os.listdir(modes_path)}")

    # Carregar imagens
    for i in range(1, 5):
        img_path = get_resource(f'Resources/Modes/{i}.png')
        print(f"Imagem {i} carregada de: {img_path}")

except Exception as e:
    print(f"ERRO: {str(e)}")
    input("Pressione Enter para sair...")
    sys.exit(1)



def main():
    nova_tela = tk.Tk()
    nova_tela.mainloop()


def abrir_outra_tela():
    print("Abrindo nova tela...")
    cap.release()
    cv2.destroyAllWindows()
    root.destroy()  # Fecha a janela principal atual do Tk

    import ScreenRegister
    ScreenRegister.main()  # Abre a outra janela


# Funções auxiliares para interação com Supabase
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



# Loop principal
while True:



    success, img = cap.read()
    if not success:
        print("Falha ao capturar frame da câmera")
        break
    print(f"Encodings conhecidos carregados: {len(encodeListKnown)}")
    img_resized = cv2.resize(img, (640, 480))
    imgS = cv2.resize(img_resized, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    cv2.imshow("Face Attendance", imgBackground)
    key = cv2.waitKey(1)

    if key == ord('+'):  # Exemplo: tecla "SHIFT e +"
        print("Tecla 'a' pressionada. Abrindo nova tela...")
        abrir_outra_tela()

    # Detecta rostos e codifica
    faceCurFrame = face_recognition.face_locations(imgS)
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    # Atualiza background com imagem da câmera e modo atual
    imgBackground[162:162 + 480, 55:55 + 640] = img_resized
    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

            if len(faceDis) > 0:
                matchIndex = np.argmin(faceDis)
                if matches[matchIndex]:
                    y1, x2, y2, x1 = [val * 4 for val in faceLoc]  # Ajusta escala para imagem original
                    bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                    imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                    id = studentIds[matchIndex]
                    if counter == 0:
                        cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                        cv2.imshow("Face Attendance", imgBackground)
                        cv2.waitKey(1)
                        counter = 1
                        modeType = 1
            else:
                print("Nenhum encoding conhecido ou face detectada para comparar.")

        if counter != 0:
            if counter == 1:
                studentInfo = get_student_info(id)

                if studentInfo is None:
                    print(f"❌ Nenhum aluno encontrado com id: {id}")
                    continue  # Pula para o próximo rosto detectado

                print(studentInfo)
                imgStudent = get_student_image(id)

                last_attendance_str = studentInfo.get('last_attendance_time')  # Agora é seguro

                if last_attendance_str:
                    datetimeObject = datetime.fromisoformat(last_attendance_str)
                    secondsElapsed = (datetime.now(datetimeObject.tzinfo) - datetimeObject).total_seconds()
                else:
                    secondsElapsed = 99999  # Força atualização caso nunca tenha registrado

                if secondsElapsed > 30:
                    update_attendance(id, studentInfo['total_attendance'] + 1)
                else:
                    print(f"Aluno {studentInfo['name']} já registrado recentemente. Ignorando novo registro.")
                    modeType = 4
                    counter = 100  # força pular os próximos blocos que fazem exibição
                    continue  # pula o restante do loop para evitar reprocessamento

            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2

                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if counter <= 10:

                    data_completa = studentInfo['last_attendance_time']
                    ano = data_completa.split('-')[0]

                    cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['group']), (1006, 550), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(id), (1006, 493), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['phone']), (910, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    #cv2.putText(imgBackground, str(studentInfo['year']), (1025, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, ano, (1125, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    (w, h), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2
                    cv2.putText(imgBackground, str(studentInfo['name']), (808 + offset, 445), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    if imgStudent is not None:
                        imgStudent = cv2.resize(imgStudent, (216, 216))
                        imgBackground[175:175 + 216, 909:909 + 216] = imgStudent
                    else:
                        print(f"❌ Erro ao carregar imagem do aluno com id {id}")

                counter += 1
                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = []
                    imgStudent = []
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
    else:
        modeType = 0
        counter = 0

    cv2.imshow("Face Attendance", imgBackground)
    if cv2.waitKey(1) & 0xFF == 27:  # Pressione ESC para sair
        break

cap.release()
cv2.destroyAllWindows()