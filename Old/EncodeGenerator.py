import cv2
import face_recognition
import pickle
import os
from supabase import create_client

# Supabase config
url = "https://jtqxscwmjjaandwujsxq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTE0MzYwNSwiZXhwIjoyMDY0NzE5NjA1fQ.yPXNbMP0-u3uwBTX8n-ymKIxH0S1mJV9D4TjLRC7DNk"  # sua anon key
supabase = create_client(url, key)

# Pasta com as imagens
folderPath = 'Images'
pathList = os.listdir(folderPath)
print("Imagens encontradas:", pathList)

imgList = []
studentIds = []

for path in pathList:
    full_path = os.path.join(folderPath, path)

    # Carrega a imagem
    image = cv2.imread(full_path)
    imgList.append(image)

    # Extrai ID do aluno (nome do arquivo)
    student_id = os.path.splitext(path)[0]
    studentIds.append(student_id)

    # 🔼 Faz upload da imagem para o bucket "student-images"
    with open(full_path, "rb") as f:
        response = supabase.storage.from_('storageforphotos').upload(
            path,
            f,
            file_options={
                "cacheControl": "3600",
                "x-upsert": "true"  # <- Passa o upsert como string no cabeçalho
            }
        )
        print(f"Upload de {path}: {response}")

print("IDs dos estudantes:", studentIds)

# Faz o encoding das imagens
def findEncodings(imagesList):
    encodeList = []
    for img in imagesList:
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_img)
        if encodings:
            encodeList.append(encodings[0])
        else:
            print("Nenhum rosto encontrado em uma imagem.")
    return encodeList

print("Iniciando encoding...")
encodeListKnown = findEncodings(imgList)
encodeListKnownWithIds = [encodeListKnown, studentIds]
print("Encoding finalizado.")

# Salva o arquivo de encoding
with open("../EncodeFile.p", 'wb') as file:
    pickle.dump(encodeListKnownWithIds, file)
print("Arquivo de encoding salvo como EncodeFile.p")
