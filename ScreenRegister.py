import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import random
import cv2
from PIL import Image, ImageTk
from supabase import create_client
import pickle
import face_recognition

# Supabase config
url = "https://jtqxscwmjjaandwujsxq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
keyStorage = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTE0MzYwNSwiZXhwIjoyMDY0NzE5NjA1fQ.yPXNbMP0-u3uwBTX8n-ymKIxH0S1mJV9D4TjLRC7DNk"

supabase = create_client(url, key)
supabaseStorage = create_client(url, keyStorage)

# Globals
id_unico = None
cam = None
preview_running = False
folderPath = 'Images'
os.makedirs(folderPath, exist_ok=True)
total_atendimentos = 0
dados_usuario = None  # Armazenará os dados antes do upload final


def main():
    nova_tela = tk.Tk()
    nova_tela.mainloop()

def gerar_id_unico():
    numeros = random.sample(range(10), 6)
    return ''.join(map(str, numeros))

def obter_total_atendimentos():
    try:
        response = supabase.table("FaceAttendenceRealTime").select("total_attendance").order("total_attendance",
                                                                                             desc=True).limit(
            1).execute()
        if response.data:
            return response.data[0]['total_attendance'] + 1
        return 1
    except Exception as e:
        print(f"Erro ao obter total de atendimentos: {e}")
        return 1


def salvar_dados_locais():
    """Armazena os dados localmente antes da captura da foto"""
    global id_unico, total_atendimentos, dados_usuario

    # Validação dos campos obrigatórios
    if not all([entry_name.get(), entry_group.get(), entry_phone.get(), entry_event.get()]):
        messagebox.showerror("Erro", "Por favor, preencha todos os campos obrigatórios!")
        return False

    try:
        id_unico = gerar_id_unico()
        total_atendimentos = obter_total_atendimentos()

        dados_usuario = {
            "id": id_unico,
            "name": entry_name.get(),
            "group": entry_group.get(),
            "phone": entry_phone.get(),
            "event": entry_event.get(),
            "total_attendance": total_atendimentos,
            "last_attendance_time": datetime.now().isoformat()
        }

        # Atualiza o contador na interface
        entry_total_attendance.config(state='normal')
        entry_total_attendance.delete(0, tk.END)
        entry_total_attendance.insert(0, str(total_atendimentos))
        entry_total_attendance.config(state='readonly')

        messagebox.showinfo("Sucesso", f"Dados prontos para envio!\nID: {id_unico}\nPosicione-se para a foto.")
        return True
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao preparar dados: {e}")
        return False


def enviar_tudo():
    """Envia dados e foto para o Supabase"""
    global dados_usuario, root  # Adicionei root como global

    if dados_usuario is None:
        messagebox.showerror("Erro", "Dados do usuário não encontrados!")
        return

    try:
        # Envia os dados para a tabela principal
        resp = supabase.table("FaceAttendenceRealTime").upsert(dados_usuario).execute()

        # Envia a foto para o storage
        path = f"Images/{id_unico}.png"
        with open(path, "rb") as f:
            supabaseStorage.storage.from_('storageforphotos').upload(
                f"{id_unico}.png",
                f,
                file_options={"cacheControl": "3600", "x-upsert": "true"}
            )

        # Atualiza os encodings para reconhecimento
        atualizar_encode_file()

        messagebox.showinfo("Sucesso", f"Registro completo!\nID: {id_unico}\nTotal Atendimentos: {total_atendimentos}")

        # Pergunta ao usuário se deseja voltar ou criar novo cadastro
        resposta = messagebox.askyesno("Opções", "Cadastro concluído com sucesso!\nDeseja criar um novo cadastro?",
                                       detail="Clique em 'Sim' para novo cadastro ou 'Não' para voltar ao menu principal")

        if resposta:
            limpar_campos()  # Limpa os campos para novo cadastro
        else:
            root.destroy()  # Fecha a janela atual
            import Main  # Importa o script principal
            Main.main()  # Executa a função principal do Main.py

    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao enviar dados completos: {e}")


def abrir_webcam():
    global cam, preview_running
    if cam is None or not cam.isOpened():
        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    preview_running = True
    mostrar_preview()
    btn_capturar.config(state=tk.NORMAL)


def capturar_foto():
    global cam, id_unico, preview_running

    if cam is None or not cam.isOpened():
        messagebox.showerror("Erro", "A webcam não está aberta.")
        return

    ret, frame = cam.read()
    if not ret:
        messagebox.showerror("Erro", "Não foi possível capturar a imagem.")
        return

    frame = cv2.flip(frame, 1)
    path = f"Images/{id_unico}.png"
    cv2.imwrite(path, frame)

    # Fecha a câmera
    preview_running = False
    cam.release()
    video_label.config(image='')

    # Envia tudo para o Supabase
    enviar_tudo()


def mostrar_preview():
    global cam, preview_running
    if cam is not None and preview_running:
        ret, frame = cam.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), (0, 255, 0), 2)

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        video_label.after(10, mostrar_preview)


def atualizar_encode_file():
    imgList = []
    studentIds = []

    for filename in os.listdir(folderPath):
        if filename.endswith(".png"):
            img_path = os.path.join(folderPath, filename)
            img = cv2.imread(img_path)
            imgList.append(img)
            studentIds.append(os.path.splitext(filename)[0])

    encodeListKnown = findEncodings(imgList)
    encodeListKnownWithIds = [encodeListKnown, studentIds]

    with open("EncodeFile.p", 'wb') as file:
        pickle.dump(encodeListKnownWithIds, file)


def findEncodings(imagesList):
    encodeList = []
    for img in imagesList:
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_img)
        if encodings:
            encodeList.append(encodings[0])
    return encodeList


def limpar_campos():
    """Limpa os campos após registro completo"""
    entry_name.delete(0, tk.END)
    entry_group.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_event.delete(0, tk.END)
    btn_capturar.config(state=tk.DISABLED)


def on_closing():
    global cam, preview_running
    if cam is not None and cam.isOpened():
        preview_running = False
        cam.release()
    root.destroy()


# --- Interface Aprimorada ---
root = tk.Tk()
root.title("Sistema de Registro com Reconhecimento Facial")
root.geometry("900x800")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_closing)

# Estilo
style = ttk.Style()
style.configure('TFrame', background='#f0f0f0')
style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
style.configure('TButton', font=('Arial', 10), padding=5)
style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

# Frame principal
main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

# Frame de formulário
form_frame = ttk.Frame(main_frame)
form_frame.grid(row=0, column=0, padx=10, pady=10, sticky=tk.N)

# Frame da webcam
webcam_frame = ttk.Frame(main_frame)
webcam_frame.grid(row=0, column=1, padx=10, pady=10)

# Título
ttk.Label(form_frame, text="Cadastro Reconhecimento Facial", style='Header.TLabel').grid(row=0, column=0,columnspan=2, pady=10)

# Campos do formulário
fields = [
    ("Nome*:", "entry_name"),
    ("Grupo*:", "entry_group"),
    ("Telefone*:", "entry_phone"),
    ("Evento*:", "entry_event"),
    ("Total Atendimentos:", "entry_total_attendance")
]

entries = {}
for i, (text, var_name) in enumerate(fields, start=1):
    label = ttk.Label(form_frame, text=text)
    label.grid(row=i, column=0, sticky='e', padx=5, pady=5)

    if "Total" in text:
        entry = ttk.Entry(form_frame, width=25, state='readonly')
    else:
        entry = ttk.Entry(form_frame, width=25)

    entry.grid(row=i, column=1, padx=5, pady=5)
    entries[var_name] = entry

# Atribui as entradas
entry_name = entries['entry_name']
entry_group = entries['entry_group']
entry_phone = entries['entry_phone']
entry_event = entries['entry_event']
entry_total_attendance = entries['entry_total_attendance']

# Botão principal que inicia o processo
btn_iniciar = ttk.Button(form_frame, text="Iniciar Registro", command=lambda: salvar_dados_locais() and abrir_webcam())
btn_iniciar.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10, sticky='ew')

# Botão de captura (inicialmente desabilitado)
btn_capturar = ttk.Button(form_frame, text="Capturar Foto", command=capturar_foto, state=tk.DISABLED)
btn_capturar.grid(row=len(fields) + 2, column=0, columnspan=2, pady=5, sticky='ew')

# Área da webcam
video_label = tk.Label(webcam_frame, bg='black', width=640, height=480,  borderwidth=2, relief='groove')
video_label.pack()

# Frame superior para instruções
top_frame = ttk.Frame(main_frame)
top_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 20))

# Instruções
instructions = ttk.Label(main_frame,
                         text="* Campos obrigatórios\n\n1. Preencha os dados\n2. Clique em 'Iniciar Registro'\n3. Posicione-se no retângulo\n4. Clique em 'Capturar Foto'",
                         justify=tk.LEFT)
instructions.grid(row=1, column=0, columnspan=2, pady=10)

root.mainloop()