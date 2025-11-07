import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os


class StartScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configurar_janela()
        self.configurar_estilos()
        self.criar_interface()
        self.process = None  # armazenar processo aberto
        self.reports_process = None  # processo específico para relatórios

    def configurar_janela(self):
        """Configura a janela principal"""
        self.title("272 Club - Sistema de Registro")
        self.configure(bg="#0f0f23")
        self.centralizar_janela(500, 800)
        self.resizable(False, False)

        # Ícone da janela (se disponível)
        try:
            self.iconbitmap("icon.ico")
        except:
            pass

    def configurar_estilos(self):
        """Configura os estilos modernos"""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configurar estilo dos botões
        self.style.configure("Modern.TButton",
                             background="#1e1e3f",
                             foreground="white",
                             borderwidth=0,
                             focuscolor="none",
                             font=("Segoe UI", 11, "bold"))

        self.style.map("Modern.TButton",
                       background=[('active', '#2d2d5a'),
                                   ('pressed', '#404080')])

    def centralizar_janela(self, largura, altura):
        """Centraliza a janela na tela"""
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        x = (largura_tela // 2) - (largura // 2)
        y = (altura_tela // 2) - (altura // 2)
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def criar_interface(self):
        """Cria toda a interface da aplicação"""
        # Container principal
        main_container = tk.Frame(self, bg="#0f0f23")
        main_container.pack(fill="both", expand=True, padx=30, pady=40)

        self.criar_header(main_container)
        self.criar_menu_principal(main_container)
        self.criar_footer(main_container)

    def criar_header(self, parent):
        """Cria o cabeçalho da aplicação"""
        header_frame = tk.Frame(parent, bg="#1a1a3a", height=120)
        header_frame.pack(fill="x", pady=(0, 30))
        header_frame.pack_propagate(False)

        # Ícone principal
        icon_label = tk.Label(
            header_frame,
            text="🎯",
            font=("Segoe UI", 40),
            bg="#1a1a3a",
            fg="#00d4ff"
        )
        icon_label.pack(pady=(0, 0))

        # Título principal
        title_label = tk.Label(
            header_frame,
            text="272 Club",
            font=("Segoe UI", 25, "bold"),
            bg="#1a1a3a",
            fg="white"
        )
        title_label.pack()

        # Subtítulo
        subtitle_label = tk.Label(
            header_frame,
            text="Sistema Avançado de Reconhecimento Facial",
            font=("Segoe UI", 10),
            bg="#1a1a3a",
            fg="#a0a0a0"
        )
        subtitle_label.pack(pady=(5, 10))

    def criar_menu_principal(self, parent):
        """Cria o menu principal com opções"""
        menu_frame = tk.Frame(parent, bg="#0f0f23")
        menu_frame.pack(fill="both", expand=True, pady=20)

        # Título do menu
        menu_title = tk.Label(
            menu_frame,
            text="Selecione uma opção:",
            font=("Segoe UI", 14, "bold"),
            bg="#0f0f23",
            fg="white"
        )
        menu_title.pack(pady=(0, 30))

        # Container dos botões
        buttons_container = tk.Frame(menu_frame, bg="#0f0f23")
        buttons_container.pack(fill="x")

        # Botão Verificar Registro
        self.criar_botao_opcao(
            buttons_container,
            "🔍 Verificar Registro",
            "Identificar usuário cadastrado",
            "#2ecc71",
            "#27ae60",
            self.open_main
        )

        # Espaçamento
        tk.Frame(buttons_container, bg="#0f0f23", height=20).pack()

        # Botão Novo Registro
        self.criar_botao_opcao(
            buttons_container,
            "📝 Novo Registro",
            "Cadastrar novo usuário",
            "#3498db",
            "#2980b9",
            self.open_register
        )

        # Espaçamento
        tk.Frame(buttons_container, bg="#0f0f23", height=20).pack()

        # Novo botão: Relatórios
        self.criar_botao_opcao(
            buttons_container,
            "📊 Relatórios",
            "Visualizar dados e estatísticas (execução independente)",
            "#f1c40f",
            "#f39c12",
            self.open_reports
        )

    def criar_botao_opcao(self, parent, texto, descricao, cor_normal, cor_hover, comando):
        """Cria um botão de opção estilizado"""
        # Container do botão
        button_container = tk.Frame(parent, bg="#1a1a3a", relief="flat", bd=1)
        button_container.pack(fill="x", pady=5)

        # Frame interno do botão
        button_frame = tk.Frame(button_container, bg=cor_normal, cursor="hand2")
        button_frame.pack(fill="x", padx=2, pady=2)

        # Texto principal
        main_label = tk.Label(
            button_frame,
            text=texto,
            font=("Segoe UI", 14, "bold"),
            bg=cor_normal,
            fg="white",
            cursor="hand2"
        )
        main_label.pack(pady=(15, 5))

        # Descrição
        desc_label = tk.Label(
            button_frame,
            text=descricao,
            font=("Segoe UI", 10),
            bg=cor_normal,
            fg="#f0f0f0",
            cursor="hand2"
        )
        desc_label.pack(pady=(0, 15))

        # Efeitos hover
        def on_enter(event):
            button_frame.config(bg=cor_hover)
            main_label.config(bg=cor_hover)
            desc_label.config(bg=cor_hover)

        def on_leave(event):
            button_frame.config(bg=cor_normal)
            main_label.config(bg=cor_normal)
            desc_label.config(bg=cor_normal)

        def on_click(event):
            comando()

        # Bind eventos para todos os elementos
        for widget in [button_frame, main_label, desc_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

    def criar_footer(self, parent):
        """Cria o rodapé da aplicação"""
        footer_frame = tk.Frame(parent, bg="#0f0f23")
        footer_frame.pack(side="bottom", fill="x", pady=(30, 0))

        # Status
        self.status_label = tk.Label(
            footer_frame,
            text="💡 Sistema pronto para uso",
            font=("Segoe UI", 9),
            bg="#0f0f23",
            fg="#00d4ff"
        )
        self.status_label.pack()

        # Separador
        separator = tk.Frame(footer_frame, bg="#333", height=1)
        separator.pack(fill="x", pady=10)

        # Informações do sistema
        info_label = tk.Label(
            footer_frame,
            text="272 Club Pro v2.0 • Powered by Yago de Souza França",
            font=("Segoe UI", 8),
            bg="#0f0f23",
            fg="#666"
        )
        info_label.pack()

    def open_main(self):
        """Abre o script de verificação"""
        self.open_script("Scripts/face_recognition_offline.py", "🔍 Verificação de Registro")

    def open_register(self):
        """Abre o script de registro"""
        self.open_script("Register.py", "📝 Novo Registro")

    def open_reports(self):
        """Abre o script de relatórios (execução independente)"""
        self.open_reports_script("event_controller_offline.py", "📊 Relatórios")

    def open_script(self, script_name, action_name):
        """Abre um script Python com feedback visual (para verificação e registro)"""
        if self.process and self.process.poll() is None:
            self.mostrar_aviso("⚠️ Processo Ativo",
                               "Já existe uma janela de verificação/registro aberta.\nFeche-a antes de abrir outra.")
            return

        try:
            self.status_label.config(
                text=f"🚀 Iniciando: {action_name}...",
                fg="#ffaa00"
            )
            self.update()

            # Verificar se o arquivo existe
            if not os.path.exists(script_name):
                self.mostrar_erro("❌ Arquivo Não Encontrado",
                                  f"O arquivo '{script_name}' não foi encontrado.")
                self.status_label.config(
                    text="❌ Erro ao iniciar processo",
                    fg="#ff4444"
                )
                return

            python_cmd = "python" if os.name == "nt" else "python3"
            self.process = subprocess.Popen([python_cmd, script_name])

            self.status_label.config(
                text=f"✅ {action_name} iniciado com sucesso",
                fg="#00ff88"
            )

            # Voltar ao status normal após 3 segundos
            self.after(3000, self.resetar_status)

        except Exception as e:
            self.mostrar_erro("❌ Erro de Execução",
                              f"Erro ao executar '{script_name}':\n{str(e)}")
            self.status_label.config(
                text="❌ Erro ao iniciar processo",
                fg="#ff4444"
            )

    def open_reports_script(self, script_name, action_name):
        """Abre o script de relatórios com execução independente"""
        # Verificar se já existe um processo de relatórios ativo
        if self.reports_process and self.reports_process.poll() is None:
            self.mostrar_aviso("⚠️ Relatórios Já Abertos",
                               "A janela de relatórios já está aberta.\nFeche-a antes de abrir outra.")
            return

        try:
            self.status_label.config(
                text=f"🚀 Iniciando: {action_name}...",
                fg="#ffaa00"
            )
            self.update()

            # Verificar se o arquivo existe
            if not os.path.exists(script_name):
                self.mostrar_erro("❌ Arquivo Não Encontrado",
                                  f"O arquivo '{script_name}' não foi encontrado.")
                self.status_label.config(
                    text="❌ Erro ao iniciar processo",
                    fg="#ff4444"
                )
                return

            python_cmd = "python" if os.name == "nt" else "python3"
            self.reports_process = subprocess.Popen([python_cmd, script_name])

            self.status_label.config(
                text=f"✅ {action_name} iniciado com sucesso (execução independente)",
                fg="#00ff88"
            )

            # Voltar ao status normal após 3 segundos
            self.after(3000, self.resetar_status)

        except Exception as e:
            self.mostrar_erro("❌ Erro de Execução",
                              f"Erro ao executar '{script_name}':\n{str(e)}")
            self.status_label.config(
                text="❌ Erro ao iniciar processo",
                fg="#ff4444"
            )

    def resetar_status(self):
        """Reseta o status para o padrão"""
        self.status_label.config(
            text="💡 Sistema pronto para uso",
            fg="#00d4ff"
        )

    def mostrar_aviso(self, titulo, mensagem):
        """Mostra mensagem de aviso estilizada"""
        messagebox.showwarning(titulo, mensagem)

    def mostrar_erro(self, titulo, mensagem):
        """Mostra mensagem de erro estilizada"""
        messagebox.showerror(titulo, mensagem)

    def on_closing(self):
        """Método chamado quando a janela é fechada"""
        # Fechar processos ativos se existirem
        if self.process and self.process.poll() is None:
            self.process.terminate()

        if self.reports_process and self.reports_process.poll() is None:
            self.reports_process.terminate()

        self.destroy()


if __name__ == "__main__":
    app = StartScreen()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)  # Configurar fechamento
    app.mainloop()