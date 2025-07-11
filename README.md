# RecognizeFaceID 🔍

Sistema de reconhecimento facial que identifica rostos em imagens e vídeos usando aprendizado de máquina.  

---

## 🧠 Funcionalidades

- Detecta rostos em imagens e vídeos.
- Reconhece identidades com base em um banco de dados.
- Interface CLI simples para:
  - Treinar modelo com novas imagens de pessoas.
  - Realizar reconhecimento em imagens/vídeos.
- Suporte a webcam ao vivo (opcional).

---

## 🚀 Tecnologias

- Python 3.8+
- [OpenCV](https://opencv.org) – captura e processamento de imagens.
- [dlib](http://dlib.net) ou Modelos pré-treinados – extração de embeddings faciais.
- Classificador (SVM, K‑NN ou rede neural leve) para reconhecimento.

---

## 💾 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/YagoFranca/RecognizeFaceID.git
   cd RecognizeFaceID
