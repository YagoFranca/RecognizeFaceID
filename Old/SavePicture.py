import cv2
import random
import os

# Função para gerar ID de 6 dígitos únicos
def gerar_id_unico():
    return ''.join(random.sample('0123456789', 6))

# Caminho de destino
diretorio_destino = os.path.join("../Images")
os.makedirs(diretorio_destino, exist_ok=True)

# Inicializa a webcam
cap = cv2.VideoCapture(0)

print("Pressione 's' para capturar a imagem...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Não foi possível acessar a webcam.")
        break

    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord('s'):
        resized_img = cv2.resize(frame, (120, 120))

        id_unico = gerar_id_unico()
        nome_arquivo = f"{id_unico}.png"
        caminho_completo = os.path.join(diretorio_destino, nome_arquivo)

        cv2.imwrite(caminho_completo, resized_img)
        print(f"✅ Imagem salva em: {caminho_completo}")
        break

cap.release()
cv2.destroyAllWindows()
