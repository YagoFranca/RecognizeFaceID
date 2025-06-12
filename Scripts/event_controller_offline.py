"""
Sistema de Controle de Eventos Integrado com Banco Local
Versão Offline-First do Sistema Original
Autor: Sistema de Reconhecimento Facial
"""

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
import threading
import time
import os
from turtle import fd

# Importar módulos do sistema offline
from local_database import LocalDatabase, serialize_encoding, deserialize_encoding
from sync_manager import create_sync_manager_from_config


class EventoControllerOffline:
    """Controlador de eventos com suporte offline e sincronização"""

    def __init__(self):
        # Inicializar banco local e sincronização
        self.local_db = LocalDatabase()
        self.sync_manager = create_sync_manager_from_config()

        # Variáveis de controle do evento
        self.evento_aberto = False
        self.evento_info = {}
        self.participantes_presenciais = []
        self.ultimo_registro_verificado = None
        self.monitoramento_ativo = False
        self.thread_monitoramento = None

        # Status de conexão
        self.has_internet = False
        self.auto_sync_enabled = True

        # Iniciar sincronização automática
        self.start_auto_sync()

    def start_auto_sync(self):
        """Inicia sincronização automática em background"""

        def auto_sync_worker():
            while self.auto_sync_enabled:
                try:
                    # Verificar conexão
                    self.has_internet = self.sync_manager.check_internet_connection()

                    # Atualizar status na UI se disponível
                    if hasattr(self, 'connection_status_label'):
                        status_text = "🌐 Online" if self.has_internet else "📴 Offline"
                        color = "green" if self.has_internet else "red"
                        self.janela.after(0, lambda: self.connection_status_label.config(
                            text=status_text, fg=color))

                    if self.has_internet:
                        # Fazer sincronização automática a cada 30 segundos
                        result = self.sync_manager.full_sync()
                        print(f"🔄 Sincronização automática: {result}")

                    # Aguardar 30 segundos antes da próxima verificação
                    time.sleep(30)

                except Exception as e:
                    print(f"Erro na sincronização automática: {e}")
                    time.sleep(30)

        # Iniciar thread de sincronização
        sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
        sync_thread.start()

    def abrir_evento(self):
        """Abre um novo evento"""
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
        """Fecha o evento atual"""
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
        """Adiciona participante manualmente"""
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

    def monitorar_banco_dados_local(self):
        """Monitora mudanças no banco de dados local"""
        print("🔍 Iniciando monitoramento do banco de dados local...")

        while self.monitoramento_ativo:
            try:
                if self.evento_aberto:
                    # Busca registros recentes (últimos 30 segundos)
                    agora = datetime.now()
                    tempo_limite = agora.replace(second=agora.second - 30 if agora.second >= 30 else agora.second + 30,
                                                 minute=agora.minute - 1 if agora.second < 30 else agora.minute)

                    # Buscar registros do banco local que foram atualizados recentemente
                    registros = self.local_db.get_all_registrations()

                    for registro in registros:
                        student_id = registro.get('id')
                        nome = registro.get('name')
                        ultima_presenca = registro.get('last_attendance_time')

                        # Verifica se é um novo registro
                        if ultima_presenca and (self.ultimo_registro_verificado is None or
                                                ultima_presenca > self.ultimo_registro_verificado):

                            # Converte para formato de hora
                            try:
                                dt = datetime.fromisoformat(ultima_presenca)

                                # Verifica se foi nos últimos 30 segundos
                                if (agora - dt).total_seconds() <= 30:
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
            self.ultimo_registro_verificado = datetime.now().isoformat()
            self.thread_monitoramento = threading.Thread(target=self.monitorar_banco_dados_local, daemon=True)
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

    def sincronizar_manual(self):
        """Executa sincronização manual"""
        if not self.has_internet:
            messagebox.showwarning("Sem Conexão", "Não há conexão com a internet para sincronização.")
            return

        try:
            self.sync_button.config(state="disabled", text="🔄 Sincronizando...")
            result = self.sync_manager.full_sync()

            # Mostrar resultado
            if result['status'] == 'success':
                message = f"Sincronização concluída!\n\nUploads: {result['uploads_success']}\nDownloads: {result['downloads']}"
                messagebox.showinfo("Sincronização", message)
            else:
                messagebox.showerror("Erro", result['message'])

        except Exception as e:
            messagebox.showerror("Erro", f"Erro na sincronização: {e}")
        finally:
            self.sync_button.config(state="normal", text="🔄 Sincronizar")

    def mostrar_registros_locais(self):
        """Mostra janela com registros do banco local"""
        registros = self.local_db.get_all_registrations()
        stats = self.local_db.get_database_stats()

        # Criar janela de registros
        registros_window = tk.Toplevel(self.janela)
        registros_window.title("Registros do Banco Local")
        registros_window.geometry("900x600")
        registros_window.configure(bg="#f0f0f0")

        # Header com estatísticas
        header_frame = tk.Frame(registros_window, bg="#f0f0f0")
        header_frame.pack(fill="x", padx=10, pady=10)

        stats_text = f"Total: {stats['total_registrations']} | Pendentes: {stats['pending_sync']} | Sincronizados: {stats['synced']} | Erros: {stats['error']}"
        tk.Label(header_frame, text=stats_text, bg="#f0f0f0", fg="black", font=("Arial", 12, "bold")).pack(pady=10)

        # Tabela de registros
        columns = ("ID", "Nome", "Grupo", "Telefone", "Status Sync", "Última Atualização")
        tree = ttk.Treeview(registros_window, columns=columns, show="headings", height=20)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)

        # Scrollbar
        scrollbar = ttk.Scrollbar(registros_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Adicionar registros
        for registro in registros:
            status_icon = {"pending": "⏳", "synced": "✅", "error": "❌"}.get(registro['sync_status'], "❓")
            tree.insert("", "end", values=(
                registro['id'],
                registro['name'],
                registro['group_name'],
                registro['phone'],
                f"{status_icon} {registro['sync_status']}",
                registro['updated_at'][:19] if registro['updated_at'] else 'N/A'
            ))

        tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 10))

    def mostrar_registros_locais(self):
        """Mostra janela com registros do banco local com opções de edição"""
        registros = self.local_db.get_all_registrations()
        stats = self.local_db.get_database_stats()

        # Criar janela de registros
        self.registros_window = tk.Toplevel(self.janela)
        self.registros_window.title("Registros do Banco Local - Editor")
        self.registros_window.geometry("1000x700")
        self.registros_window.configure(bg="#f0f0f0")

        # Header com estatísticas
        header_frame = tk.Frame(self.registros_window, bg="#f0f0f0")
        header_frame.pack(fill="x", padx=10, pady=10)

        stats_text = f"Total: {stats['total_registrations']} | Pendentes: {stats['pending_sync']} | Sincronizados: {stats['synced']} | Erros: {stats['error']}"
        tk.Label(header_frame, text=stats_text, bg="#f0f0f0", fg="black", font=("Arial", 12, "bold")).pack(pady=5)

        # Frame principal para tabela e botões
        main_frame = tk.Frame(self.registros_window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame para botões de ação
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.pack(fill="x", pady=(0, 10))

        # Botões de ação
        tk.Button(buttons_frame, text="Editar Selecionado", command=lambda: self.editar_registro_selecionado(),
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        tk.Button(buttons_frame, text="Excluir Selecionado", command=lambda: self.excluir_registro_selecionado(),
                  bg="#f44336", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)

        tk.Button(buttons_frame, text="Novo Registro", command=lambda: self.novo_registro(),
                  bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)

        tk.Button(buttons_frame, text="Atualizar Lista", command=lambda: self.atualizar_lista_registros(),
                  bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)

        # Frame para tabela
        table_frame = tk.Frame(main_frame, bg="#f0f0f0")
        table_frame.pack(fill="both", expand=True)

        # Tabela de registros
        columns = ("ID", "Nome", "Grupo", "Telefone", "Status Sync", "Última Atualização")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.tree.heading(col, text=col)
            if col == "Nome":
                self.tree.column(col, width=200)
            elif col == "Grupo":
                self.tree.column(col, width=150)
            elif col == "Telefone":
                self.tree.column(col, width=120)
            elif col == "Última Atualização":
                self.tree.column(col, width=150)
            else:
                self.tree.column(col, width=100)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Carregar registros
        self.carregar_registros()

        # Posicionar elementos
        self.tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Bind duplo clique para editar
        self.tree.bind("<Double-1>", lambda e: self.editar_registro_selecionado())

    def carregar_registros(self):
        """Carrega registros na tabela"""
        # Limpar tabela
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Carregar registros
        registros = self.local_db.get_all_registrations()
        for registro in registros:
            status_icon = {"pending": "⏳", "synced": "✅", "error": "❌"}.get(registro['sync_status'], "❓")
            self.tree.insert("", "end", values=(
                registro['id'],
                registro['name'],
                registro['group_name'],
                registro['phone'],
                f"{status_icon} {registro['sync_status']}",
                registro['updated_at'][:19] if registro['updated_at'] else 'N/A'
            ))

    def atualizar_lista_registros(self):
        """Atualiza a lista de registros"""
        self.carregar_registros()
        messagebox.showinfo("Sucesso", "Lista atualizada com sucesso!")

    def editar_registro_selecionado(self):
        """Abre janela de edição para o registro selecionado"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um registro para editar.")
            return

        item = self.tree.item(selected[0])
        values = item['values']

        # Criar dicionário do registro com dados da tabela
        registro = {
            'id': values[0],
            'name': values[1],
            'group_name': values[2],
            'phone': values[3],
            'sync_status': values[4].replace("⏳ ", "").replace("✅ ", "").replace("❌ ", "").replace("❓ ", "")
        }

        self.abrir_janela_edicao(registro)

    def novo_registro(self):
        """Abre janela para criar novo registro"""
        registro_vazio = {
            'id': None,
            'name': '',
            'group_name': '',
            'phone': '',
            'sync_status': 'pending'
        }
        self.abrir_janela_edicao(registro_vazio, is_new=True)

    def abrir_janela_edicao(self, registro, is_new=False):
        """Abre janela de edição/criação de registro"""
        self.edit_window = tk.Toplevel(self.registros_window)
        title = "Novo Registro" if is_new else f"Editar Registro ID: {registro['id']}"
        self.edit_window.title(title)
        self.edit_window.geometry("400x300")
        self.edit_window.configure(bg="#f0f0f0")
        self.edit_window.transient(self.registros_window)
        self.edit_window.grab_set()

        # Frame principal
        main_frame = tk.Frame(self.edit_window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Campos de edição
        tk.Label(main_frame, text="Nome:", bg="#f0f0f0", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w",
                                                                                          pady=5)
        self.entry_nome = tk.Entry(main_frame, font=("Arial", 10), width=30)
        self.entry_nome.grid(row=0, column=1, pady=5, padx=(10, 0))
        self.entry_nome.insert(0, registro.get('name', ''))

        tk.Label(main_frame, text="Grupo:", bg="#f0f0f0", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w",
                                                                                           pady=5)
        self.entry_grupo = tk.Entry(main_frame, font=("Arial", 10), width=30)
        self.entry_grupo.grid(row=1, column=1, pady=5, padx=(10, 0))
        self.entry_grupo.insert(0, registro.get('group_name', ''))

        tk.Label(main_frame, text="Telefone:", bg="#f0f0f0", font=("Arial", 10, "bold")).grid(row=2, column=0,
                                                                                              sticky="w", pady=5)
        self.entry_telefone = tk.Entry(main_frame, font=("Arial", 10), width=30)
        self.entry_telefone.grid(row=2, column=1, pady=5, padx=(10, 0))
        self.entry_telefone.insert(0, registro.get('phone', ''))

        tk.Label(main_frame, text="Status Sync:", bg="#f0f0f0", font=("Arial", 10, "bold")).grid(row=3, column=0,
                                                                                                 sticky="w", pady=5)
        self.combo_status = ttk.Combobox(main_frame, values=["pending", "synced", "error"], width=27, state="readonly")
        self.combo_status.grid(row=3, column=1, pady=5, padx=(10, 0))
        self.combo_status.set(registro.get('sync_status', 'pending'))

        # Frame para botões
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.grid(row=4, column=0, columnspan=2, pady=20)

        # Botões
        tk.Button(buttons_frame, text="Salvar",
                  command=lambda: self.salvar_registro(registro['id'] if not is_new else None, is_new),
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=10).pack(side="left", padx=5)

        tk.Button(buttons_frame, text="Cancelar",
                  command=self.edit_window.destroy,
                  bg="#757575", fg="white", font=("Arial", 10, "bold"), width=10).pack(side="left", padx=5)

    def salvar_registro(self, registro_id, is_new):
        nome = self.entry_nome.get().strip()
        grupo = self.entry_grupo.get().strip()
        telefone = self.entry_telefone.get().strip()
        status = self.combo_status.get()

        if not nome:
            messagebox.showerror("Erro", "Nome é obrigatório.")
            return

        try:
            if is_new:
                messagebox.showinfo("Info", "Função de criar novo registro não implementada.")
            else:
                update_data = {
                    'name': nome,
                    'group_name': grupo,
                    'phone': telefone,
                    'sync_status': status
                }
                success = self.local_db.update_registration(registro_id, update_data)
                if success:
                    messagebox.showinfo("Sucesso", "Registro atualizado com sucesso!")
                    self.edit_window.destroy()
                    self.carregar_registros()

                    # Pergunta se quer salvar em arquivo
                    if messagebox.askyesno("Exportar", "Deseja salvar este registro em um arquivo?"):
                        self.salvar_com_dialogo()

                else:
                    messagebox.showwarning("Aviso", "Registro não encontrado ou não foi possível atualizar.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")

    def salvar_com_dialogo(self):
        # Diálogo para escolher onde salvar
        caminho = fd.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Todos os arquivos", "*.*")],
            title="Salvar arquivo como"
        )
        if not caminho:
            return  # Usuário cancelou

        # Conteúdo do CSV
        conteudo = "Nome,Grupo,Telefone,Status\n"
        conteudo += f"{self.entry_nome.get()},{self.entry_grupo.get()},{self.entry_telefone.get()},{self.combo_status.get()}\n"

        # Tentativa de salvar
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar o arquivo:\n{str(e)}")

    def exportar_lista(self):
        """Exporta a lista de participantes, permitindo ao usuário escolher o local"""
        # Verificar se há participantes para exportar
        if not hasattr(self, 'participantes_presenciais') or not self.participantes_presenciais:
            messagebox.showinfo("Aviso", "Nenhum participante para exportar.")
            return

        try:
            # Nome do arquivo sugerido
            nome_evento = getattr(self, 'evento_nome', 'evento_offline')
            nome_evento_arquivo = nome_evento.replace(' ', '_').replace('/', '-').replace('\\', '-')
            nome_sugerido = f"participantes_{nome_evento_arquivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            # Diálogo para o usuário escolher onde salvar
            caminho_completo = filedialog.asksaveasfilename(
                title="Salvar lista de participantes",
                defaultextension=".txt",
                initialfile=nome_sugerido,
                filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")]
            )

            if not caminho_completo:
                return  # Usuário cancelou

            with open(caminho_completo, 'w', encoding='utf-8') as arquivo:
                arquivo.write("LISTA DE PARTICIPANTES DO EVENTO\n")
                arquivo.write("=" * 50 + "\n\n")

                if hasattr(self, 'evento_nome'):
                    arquivo.write(f"Nome do evento: {self.evento_nome}\n")
                if hasattr(self, 'evento_inicio'):
                    arquivo.write(f"Início do evento: {self.evento_inicio}\n")
                if hasattr(self, 'evento_fim'):
                    arquivo.write(f"Fim do evento: {self.evento_fim}\n")

                arquivo.write(f"Data da exportação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                arquivo.write(f"Total de participantes: {len(self.participantes_presenciais)}\n\n")
                arquivo.write("PARTICIPANTES:\n")
                arquivo.write("-" * 80 + "\n")
                arquivo.write(f"{'#':<3} {'NOME':<30} {'HORA':<10} {'TIPO':<8} {'ID':<10}\n")
                arquivo.write("-" * 80 + "\n")

                for i, participante in enumerate(self.participantes_presenciais):
                    nome = participante.get('nome', 'N/A')
                    hora = participante.get('hora', 'N/A')
                    tipo = participante.get('tipo', 'N/A')
                    id_participante = participante.get('id', 'N/A')
                    arquivo.write(f"{i + 1:<3} {nome:<30} {hora:<10} {tipo:<8} {id_participante:<10}\n")

            messagebox.showinfo("Sucesso", f"Lista exportada com sucesso:\n{caminho_completo}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar:\n{str(e)}")

    def exportar_registros_banco(self):
        """Exporta todos os registros do banco local"""
        try:
            # Obter registros do banco
            registros = self.local_db.get_all_registrations()

            if not registros:
                messagebox.showinfo("Aviso", "Nenhum registro no banco para exportar.")
                return

            # Obter área de trabalho
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Área de Trabalho")
            if not os.path.exists(desktop):
                desktop = os.path.expanduser("~")

            # Nome do arquivo
            nome_arquivo = f"registros_banco_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            caminho_completo = os.path.join(desktop, nome_arquivo)

            with open(caminho_completo, 'w', encoding='utf-8') as arquivo:
                arquivo.write("REGISTROS DO BANCO LOCAL\n")
                arquivo.write("=" * 50 + "\n\n")
                arquivo.write(f"Data da exportação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                arquivo.write(f"Total de registros: {len(registros)}\n\n")

                arquivo.write("REGISTROS:\n")
                arquivo.write("-" * 100 + "\n")
                arquivo.write(
                    f"{'ID':<5} {'NOME':<30} {'GRUPO':<20} {'TELEFONE':<15} {'STATUS':<10} {'ATUALIZADO':<20}\n")
                arquivo.write("-" * 100 + "\n")

                for registro in registros:
                    arquivo.write(f"{str(registro.get('id', 'N/A')):<5} "
                                  f"{registro.get('name', 'N/A'):<30} "
                                  f"{registro.get('group_name', 'N/A'):<20} "
                                  f"{registro.get('phone', 'N/A'):<15} "
                                  f"{registro.get('sync_status', 'N/A'):<10} "
                                  f"{registro.get('updated_at', 'N/A')[:19]:<20}\n")

            messagebox.showinfo("Sucesso", f"Registros do banco exportados para:\n{caminho_completo}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar registros do banco: {str(e)}")

    def excluir_registro_selecionado(self):
        """Exclui o registro selecionado"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um registro para excluir.")
            return

        item = self.tree.item(selected[0])
        registro_id = item['values'][0]
        nome = item['values'][1]

        # Confirmar exclusão
        resposta = messagebox.askyesno("Confirmar Exclusão",
                                       f"Tem certeza que deseja excluir o registro:\n\nID: {registro_id}\nNome: {nome}")

        if resposta:
            try:
                # Adapte este método conforme sua implementação de LocalDatabase
                # success = self.local_db.delete_registration(registro_id)

                # Por enquanto, simularemos
                messagebox.showinfo("Info",
                                    f"Funcionalidade para excluir registro ID {registro_id} precisa ser implementada no LocalDatabase.")

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao excluir: {str(e)}")

    def limpar_lista(self):
        """Limpa a lista de participantes"""
        if messagebox.askyesno("Confirmar", "Deseja limpar toda a lista de participantes?"):
            self.participantes_presenciais.clear()
            self.atualizar_tabela()

    def criar_interface(self):
        """Cria a interface gráfica"""
        self.janela = tk.Toplevel()
        self.janela.title("Controle de Evento - Sistema Integrado (Offline-First)")
        self.janela.geometry("1000x800")
        self.janela.configure(bg='#f0f0f0')

        # Frame principal
        main_frame = tk.Frame(self.janela, bg='#f0f0f0')
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame para status de conexão
        connection_frame = tk.Frame(main_frame, bg='#f0f0f0')
        connection_frame.pack(fill="x", pady=(0, 10))

        self.connection_status_label = tk.Label(
            connection_frame,
            text="🔄 Verificando conexão...",
            font=("Arial", 10, "bold"),
            bg='#f0f0f0',
            fg='orange'
        )
        self.connection_status_label.pack(side="left")

        # Botão de sincronização manual
        self.sync_button = tk.Button(
            connection_frame,
            text="🔄 Sincronizar",
            command=self.sincronizar_manual,
            font=("Arial", 10),
            bg='#4CAF50',
            fg='white'
        )
        self.sync_button.pack(side="right", padx=(0, 10))

        # Botão para ver registros locais
        view_db_button = tk.Button(
            connection_frame,
            text="📋 Ver Banco Local",
            command=self.mostrar_registros_locais,
            font=("Arial", 10),
            bg='#2196F3',
            fg='white'
        )
        view_db_button.pack(side="right", padx=(0, 10))

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
                                       font=("Arial", 11, "bold"), bg='#f0f0f0')
        self.contador_label.pack(side="left")

        # Botões de ação
        btn_frame = tk.Frame(info_frame, bg='#f0f0f0')
        btn_frame.pack(side="right")

        btn_exportar = tk.Button(btn_frame, text="📄 Exportar",
                                 command=self.exportar_lista, font=("Arial", 9),
                                 bg='#FF9800', fg='white')
        btn_exportar.pack(side="left", padx=2)

        btn_limpar = tk.Button(btn_frame, text="🗑️ Limpar",
                               command=self.limpar_lista, font=("Arial", 9),
                               bg='#f44336', fg='white')
        btn_limpar.pack(side="left", padx=2)

        # Tabela de participantes
        table_frame = tk.Frame(participantes_frame, bg='#f0f0f0')
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Configurar colunas
        columns = ("#", "Nome", "Hora", "Tipo", "ID")
        self.tabela = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.tabela.heading(col, text=col)
            if col == "#":
                self.tabela.column(col, width=50)
            elif col == "Hora":
                self.tabela.column(col, width=80)
            elif col == "Tipo":
                self.tabela.column(col, width=80)
            elif col == "ID":
                self.tabela.column(col, width=100)
            else:
                self.tabela.column(col, width=200)

        # Scrollbar para tabela
        scrollbar_table = ttk.Scrollbar(table_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar_table.set)

        self.tabela.pack(side="left", fill="both", expand=True)
        scrollbar_table.pack(side="right", fill="y")

    def run(self):
        """Executa a interface"""
        self.criar_interface()

        # Configurar fechamento da aplicação
        def on_closing():
            self.auto_sync_enabled = False
            self.parar_monitoramento()
            self.janela.destroy()

        self.janela.protocol("WM_DELETE_WINDOW", on_closing)


def main():
    """Função principal"""
    root = tk.Tk()
    root.withdraw()  # Esconder janela principal

    controller = EventoControllerOffline()
    controller.run()

    root.mainloop()


if __name__ == "__main__":
    main()

