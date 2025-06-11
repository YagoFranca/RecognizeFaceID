import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import threading
import time
from supabase import create_client
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# Configuração Supabase (use as mesmas credenciais do seu sistema principal)
SUPABASE_URL = "https://jtqxscwmjjaandwujsxq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class EventoController:
    def __init__(self):
        self.evento_aberto = False
        self.evento_info = {}
        self.participantes_presenciais = []
        self.ultimo_registro_verificado = None
        self.monitoramento_ativo = False
        self.thread_monitoramento = None

    def abrir_evento(self):
        if self.evento_aberto:
            messagebox.showinfo("Aviso", "O evento já está aberto.")
            return

        # Verifica se o nome do evento foi preenchido
        nome_evento = self.entry_nome_evento.get().strip()
        if not nome_evento or nome_evento == "Nome do evento":
            messagebox.showwarning("Erro", "Por favor, digite o nome do evento antes de abrir.")
            return

        self.evento_info['nome'] = nome_evento
        self.evento_info['inicio'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.evento_aberto = True
        self.iniciar_monitoramento()

        status_text = f"Status: ABERTO\nEvento: {self.evento_info['nome']}\nInício: {self.evento_info['inicio']}"
        self.status_label.config(text=status_text, fg="green")

        # Desabilita o campo de nome do evento quando aberto
        self.entry_nome_evento.config(state='disabled')

        messagebox.showinfo("Evento",
                            f"Evento '{nome_evento}' aberto com sucesso!\nMonitoramento de presenças ativado.")

    def fechar_evento(self):
        if not self.evento_aberto:
            messagebox.showinfo("Aviso", "O evento já está fechado.")
            return

        self.evento_info['fim'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.evento_aberto = False
        self.parar_monitoramento()

        status_text = f"Status: FECHADO\nEvento: {self.evento_info['nome']}\nInício: {self.evento_info['inicio']}\nFim: {self.evento_info['fim']}"
        self.status_label.config(text=status_text, fg="red")

        # Reabilita o campo de nome do evento quando fechado
        self.entry_nome_evento.config(state='normal')

        # Mostra estatísticas finais
        total_participantes = len(self.participantes_presenciais)
        messagebox.showinfo("Evento",
                            f"Evento '{self.evento_info['nome']}' fechado com sucesso!\nTotal de participantes: {total_participantes}")

    def novo_evento(self):
        """Prepara o sistema para um novo evento"""
        if self.evento_aberto:
            messagebox.showwarning("Aviso", "Feche o evento atual antes de criar um novo.")
            return

        if self.participantes_presenciais:
            resposta = messagebox.askyesno("Confirmar",
                                           "Há participantes na lista atual. Deseja limpar a lista para o novo evento?")
            if resposta:
                self.participantes_presenciais.clear()
                self.atualizar_tabela()

        # Limpa o campo de nome do evento
        self.entry_nome_evento.delete(0, tk.END)
        self.entry_nome_evento.insert(0, "Nome do evento")
        self.entry_nome_evento.config(state='normal')

        # Reseta informações do evento
        self.evento_info.clear()
        self.status_label.config(text="Status: FECHADO\nPronto para novo evento", fg="red")

        messagebox.showinfo("Novo Evento", "Sistema preparado para novo evento!")

    def adicionar_participante_manual(self, nome):
        if not self.evento_aberto:
            messagebox.showwarning("Erro", "Evento não está aberto.")
            return

        if not nome or nome.strip() == "" or nome == "Nome do participante":
            messagebox.showwarning("Erro", "Digite um nome válido.")
            return

        hora = datetime.now().strftime("%H:%M:%S")
        self.participantes_presenciais.append({
            'nome': nome.strip(),
            'hora': hora,
            'tipo': 'MANUAL',
            'id': 'N/A'
        })
        self.atualizar_tabela()
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, "Nome do participante")

    def adicionar_participante_automatico(self, nome, student_id, hora=None):
        """Adiciona participante automaticamente via reconhecimento facial"""
        if not self.evento_aberto:
            return False

        if hora is None:
            hora = datetime.now().strftime("%H:%M:%S")

        # Verifica se já foi registrado no evento atual
        for participante in self.participantes_presenciais:
            if participante.get('id') == student_id:
                print(f"👥 {nome} já registrado no evento atual")
                return False

        self.participantes_presenciais.append({
            'nome': nome,
            'hora': hora,
            'tipo': 'FACIAL',
            'id': student_id
        })

        # Atualiza a interface na thread principal
        self.janela.after(0, self.atualizar_tabela)
        print(f"✅ {nome} adicionado ao evento automaticamente")
        return True

    def monitorar_banco_dados(self):
        """Monitora mudanças no banco de dados"""
        print("🔍 Iniciando monitoramento do banco de dados...")

        while self.monitoramento_ativo:
            try:
                if self.evento_aberto:
                    # Busca registros recentes (últimos 30 segundos)
                    agora = datetime.now()
                    tempo_limite = agora.replace(second=agora.second - 30 if agora.second >= 30 else agora.second + 30,
                                                 minute=agora.minute - 1 if agora.second < 30 else agora.minute)

                    resultado = supabase.table("FaceAttendenceRealTime").select("*").gte(
                        "last_attendance_time", tempo_limite.strftime("%Y-%m-%d %H:%M:%S")
                    ).execute()

                    if resultado.data:
                        for registro in resultado.data:
                            student_id = registro.get('id')
                            nome = registro.get('name')
                            ultima_presenca = registro.get('last_attendance_time')

                            # Verifica se é um novo registro
                            if ultima_presenca and (self.ultimo_registro_verificado is None or
                                                    ultima_presenca > self.ultimo_registro_verificado):

                                # Converte para formato de hora
                                try:
                                    dt = datetime.fromisoformat(ultima_presenca)
                                    hora_formatada = dt.strftime("%H:%M:%S")

                                    # Adiciona ao evento se ainda não foi registrado
                                    if self.adicionar_participante_automatico(nome, student_id, hora_formatada):
                                        self.ultimo_registro_verificado = ultima_presenca

                                except Exception as e:
                                    print(f"Erro ao processar hora: {e}")

            except Exception as e:
                print(f"Erro no monitoramento: {e}")

            time.sleep(2)  # Verifica a cada 2 segundos

    def iniciar_monitoramento(self):
        """Inicia o monitoramento em thread separada"""
        if not self.monitoramento_ativo:
            self.monitoramento_ativo = True
            self.ultimo_registro_verificado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.thread_monitoramento = threading.Thread(target=self.monitorar_banco_dados, daemon=True)
            self.thread_monitoramento.start()

    def parar_monitoramento(self):
        """Para o monitoramento"""
        self.monitoramento_ativo = False

    def atualizar_tabela(self):
        """Atualiza a tabela de participantes"""
        for row in self.tabela.get_children():
            self.tabela.delete(row)

        for i, participante in enumerate(self.participantes_presenciais):
            self.tabela.insert("", "end", values=(
                i + 1,
                participante['nome'],
                participante['hora'],
                participante['tipo'],
                participante.get('id', 'N/A')
            ))

        # Atualiza contador
        self.contador_label.config(text=f"Total: {len(self.participantes_presenciais)} participantes")

    def exportar_lista(self):
        """Exporta a lista de participantes"""
        if not self.participantes_presenciais:
            messagebox.showinfo("Aviso", "Nenhum participante para exportar.")
            return

        try:
            # Nome do arquivo incluindo o nome do evento
            nome_evento_arquivo = self.evento_info.get('nome', 'evento').replace(' ', '_').replace('/', '-')
            nome_arquivo = f"participantes_{nome_evento_arquivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            with open(nome_arquivo, 'w', encoding='utf-8') as arquivo:
                arquivo.write("LISTA DE PARTICIPANTES DO EVENTO\n")
                arquivo.write("=" * 50 + "\n\n")

                if 'nome' in self.evento_info:
                    arquivo.write(f"Nome do evento: {self.evento_info['nome']}\n")
                if 'inicio' in self.evento_info:
                    arquivo.write(f"Início do evento: {self.evento_info['inicio']}\n")
                if 'fim' in self.evento_info:
                    arquivo.write(f"Fim do evento: {self.evento_info['fim']}\n")

                arquivo.write(f"Total de participantes: {len(self.participantes_presenciais)}\n\n")
                arquivo.write("PARTICIPANTES:\n")
                arquivo.write("-" * 80 + "\n")
                arquivo.write(f"{'#':<3} {'NOME':<30} {'HORA':<10} {'TIPO':<8} {'ID':<10}\n")
                arquivo.write("-" * 80 + "\n")

                for i, participante in enumerate(self.participantes_presenciais):
                    arquivo.write(f"{i + 1:<3} {participante['nome']:<30} {participante['hora']:<10} "
                                  f"{participante['tipo']:<8} {participante.get('id', 'N/A'):<10}\n")

            messagebox.showinfo("Sucesso", f"Lista exportada para: {nome_arquivo}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")

    def limpar_lista(self):
        """Limpa a lista de participantes"""
        if messagebox.askyesno("Confirmar", "Deseja limpar toda a lista de participantes?"):
            self.participantes_presenciais.clear()
            self.atualizar_tabela()

    def criar_interface(self):
        """Cria a interface gráfica"""
        self.janela = tk.Toplevel()
        self.janela.title("Controle de Evento - Sistema Integrado")
        self.janela.geometry("900x750")
        self.janela.configure(bg='#f0f0f0')

        # Frame principal
        main_frame = tk.Frame(self.janela, bg='#f0f0f0')
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame para nome do evento
        nome_evento_frame = tk.LabelFrame(main_frame, text="Configuração do Evento",
                                          font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333')
        nome_evento_frame.pack(fill="x", pady=(0, 10))

        # Campo para nome do evento
        nome_frame = tk.Frame(nome_evento_frame, bg='#f0f0f0')
        nome_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(nome_frame, text="Nome do evento:", font=("Arial", 10), bg='#f0f0f0').pack(anchor="w")

        entrada_evento_frame = tk.Frame(nome_frame, bg='#f0f0f0')
        entrada_evento_frame.pack(fill="x", pady=5)

        self.entry_nome_evento = tk.Entry(entrada_evento_frame, font=("Arial", 11))
        self.entry_nome_evento.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_nome_evento.insert(0, "Nome do evento")

        # Botão para novo evento
        btn_novo = tk.Button(entrada_evento_frame, text="🆕 Novo Evento",
                             command=self.novo_evento, font=("Arial", 10),
                             bg='#9C27B0', fg='white')
        btn_novo.pack(side="right")

        # Placeholder para o campo de nome do evento
        def on_evento_click(event):
            if self.entry_nome_evento.get() == "Nome do evento":
                self.entry_nome_evento.delete(0, tk.END)

        def on_evento_leave(event):
            if self.entry_nome_evento.get() == "":
                self.entry_nome_evento.insert(0, "Nome do evento")

        self.entry_nome_evento.bind('<FocusIn>', on_evento_click)
        self.entry_nome_evento.bind('<FocusOut>', on_evento_leave)

        # Status do evento
        status_frame = tk.LabelFrame(main_frame, text="Status do Evento", font=("Arial", 12, "bold"),
                                     bg='#f0f0f0', fg='#333')
        status_frame.pack(fill="x", pady=(0, 10))

        self.status_label = tk.Label(status_frame, text="Status: FECHADO\nPronto para novo evento",
                                     font=("Arial", 11), bg='#f0f0f0', fg="red")
        self.status_label.pack(pady=10)

        # Botões de controle
        botoes_frame = tk.Frame(status_frame, bg='#f0f0f0')
        botoes_frame.pack(pady=5)

        btn_abrir = tk.Button(botoes_frame, text="🟢 Abrir Evento", width=15,
                              command=self.abrir_evento, font=("Arial", 10, "bold"),
                              bg='#4CAF50', fg='white')
        btn_abrir.pack(side="left", padx=5)

        btn_fechar = tk.Button(botoes_frame, text="🔴 Fechar Evento", width=15,
                               command=self.fechar_evento, font=("Arial", 10, "bold"),
                               bg='#f44336', fg='white')
        btn_fechar.pack(side="left", padx=5)

        # Frame de participantes
        participantes_frame = tk.LabelFrame(main_frame, text="Gerenciamento de Participantes",
                                            font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333')
        participantes_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Entrada manual
        entrada_frame = tk.Frame(participantes_frame, bg='#f0f0f0')
        entrada_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(entrada_frame, text="Adicionar manualmente:",
                 font=("Arial", 10), bg='#f0f0f0').pack(anchor="w")

        entrada_controls = tk.Frame(entrada_frame, bg='#f0f0f0')
        entrada_controls.pack(fill="x", pady=5)

        self.entry_nome = tk.Entry(entrada_controls, font=("Arial", 10))
        self.entry_nome.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_nome.insert(0, "Nome do participante")

        # Limpa placeholder quando clica
        def on_entry_click(event):
            if self.entry_nome.get() == "Nome do participante":
                self.entry_nome.delete(0, tk.END)

        def on_entry_leave(event):
            if self.entry_nome.get() == "":
                self.entry_nome.insert(0, "Nome do participante")

        self.entry_nome.bind('<FocusIn>', on_entry_click)
        self.entry_nome.bind('<FocusOut>', on_entry_leave)

        btn_add = tk.Button(entrada_controls, text="➕ Adicionar",
                            command=lambda: self.adicionar_participante_manual(self.entry_nome.get()),
                            font=("Arial", 10), bg='#2196F3', fg='white')
        btn_add.pack(side="right")

        # Contador e botões de ação
        info_frame = tk.Frame(participantes_frame, bg='#f0f0f0')
        info_frame.pack(fill="x", padx=10, pady=5)

        self.contador_label = tk.Label(info_frame, text="Total: 0 participantes",
                                       font=("Arial", 10, "bold"), bg='#f0f0f0', fg='#333')
        self.contador_label.pack(side="left")

        botoes_acao = tk.Frame(info_frame, bg='#f0f0f0')
        botoes_acao.pack(side="right")

        btn_exportar = tk.Button(botoes_acao, text="📤 Exportar", command=self.exportar_lista,
                                 font=("Arial", 9), bg='#FF9800', fg='white')
        btn_exportar.pack(side="left", padx=2)

        btn_limpar = tk.Button(botoes_acao, text="🗑️ Limpar", command=self.limpar_lista,
                               font=("Arial", 9), bg='#607D8B', fg='white')
        btn_limpar.pack(side="left", padx=2)

        # Nota informativa
        info_label = tk.Label(participantes_frame,
                              text="💡 Participantes serão adicionados automaticamente via reconhecimento facial quando o evento estiver aberto",
                              font=("Arial", 9), bg='#f0f0f0', fg='#666', wraplength=800)
        info_label.pack(padx=10, pady=5)

        # Tabela de participantes
        tabela_frame = tk.Frame(participantes_frame, bg='#f0f0f0')
        tabela_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tabela_frame)
        scrollbar.pack(side="right", fill="y")

        self.tabela = ttk.Treeview(tabela_frame, columns=("ID", "Nome", "Hora", "Tipo", "StudentID"),
                                   show="headings", yscrollcommand=scrollbar.set)

        # Configuração das colunas
        self.tabela.heading("ID", text="#")
        self.tabela.heading("Nome", text="Nome")
        self.tabela.heading("Hora", text="Hora")
        self.tabela.heading("Tipo", text="Tipo")
        self.tabela.heading("StudentID", text="ID Sistema")

        self.tabela.column("ID", width=50)
        self.tabela.column("Nome", width=250)
        self.tabela.column("Hora", width=100)
        self.tabela.column("Tipo", width=80)
        self.tabela.column("StudentID", width=100)

        self.tabela.pack(fill="both", expand=True)
        scrollbar.config(command=self.tabela.yview)

        # Protocolo de fechamento
        def on_closing():
            if self.monitoramento_ativo:
                self.parar_monitoramento()
            self.janela.destroy()

        self.janela.protocol("WM_DELETE_WINDOW", on_closing)

        # Testa conexão com banco
        self.testar_conexao_banco()

    def testar_conexao_banco(self):
        """Testa a conexão com o banco de dados"""
        try:
            resultado = supabase.table("FaceAttendenceRealTime").select("id").limit(1).execute()
            if resultado.data is not None:
                print("✅ Conexão com banco de dados estabelecida")
                # Adiciona indicador visual
                conexao_label = tk.Label(self.janela, text="🟢 Conectado ao banco",
                                         font=("Arial", 8), fg="green")
                conexao_label.pack(side="bottom", anchor="e", padx=10, pady=2)
            else:
                raise Exception("Sem dados retornados")
        except Exception as e:
            print(f"❌ Erro na conexão com banco: {e}")
            conexao_label = tk.Label(self.janela, text="🔴 Erro na conexão",
                                     font=("Arial", 8), fg="red")
            conexao_label.pack(side="bottom", anchor="e", padx=10, pady=2)


# Execução principal
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal

    controller = EventoController()
    controller.criar_interface()

    root.mainloop()