import tkinter as tk
from tkinter import scrolledtext
import threading
import time
from xmlrpc.client import ServerProxy

binder = ServerProxy("http://localhost:5000")
#Função para buscar servidor
def get_server_proxy(procedure):
    result = binder.lookup_procedure(procedure)
    #Verifica se o procedimento existe
    if result is None:
        raise ValueError(f"Procedimento '{procedure}' não encontrado no Binder.")
    server_address, server_port = result
    return ServerProxy(f"http://{server_address}:{server_port}", allow_none=True)

#Classe do Chat
class ChatClient:
    def __init__(self, root, username, room_name):
        #Configuração Interface
        self.root = root
        self.root.title(f"ChatRPC - Sala: {room_name}")
        
        self.username = username
        self.room_name = room_name
        self.send_server = get_server_proxy("join_room")
        self.displayed_messages = set() #mensagens exibidas no chat
        self.lock = threading.Lock() #lock para threads
        self.current_users = []  # Lista de usuários atuais na sala
        self.running = True #flag para threads

        # Criação da interface
        self.create_interface()

        # Inicia a thread para verificar mensagens
        self.start_message_thread()

        # Captura o evento de fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_interface(self):
        #Cria os componentes da interface.

        #Área de mensagens
        self.chat_area = scrolledtext.ScrolledText(self.root, state='disabled', width=50, height=20)
        self.chat_area.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

        #Campo de input
        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.grid(row=1, column=0, padx=10, pady=10, columnspan=2)

        #Caixa de seleção de destinatário
        self.user_var = tk.StringVar(self.root)
        self.user_var.set("broadcast")  # Opção inicial

        self.user_menu = tk.OptionMenu(self.root, self.user_var, "broadcast")  # Inicia com "broadcast"
        self.user_menu.grid(row=2, column=0, padx=10, pady=10, sticky="e")

        #Botão Enviar
        self.send_button = tk.Button(self.root, text="Enviar", command=self.send_message_chat)
        self.send_button.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        #Status da conexão
        self.status_label = tk.Label(self.root, text=f"Conectado como: {self.username}")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5)

    def send_message_chat(self):
        #Envia uma mensagem para o servidor de forma assíncrona.
        message = self.message_entry.get().strip()
        if not message:
            return  # Não envia mensagens vazias
        
        # Obtém o usuário selecionado
        selected_user = self.user_var.get()  # Obtém o usuário selecionado
        destination = selected_user if selected_user != "broadcast" else None

        try:
            # Inicia a thread para enviar a mensagem
            threading.Thread(target=self.send_message_thread, args=(message, destination), daemon=True).start()

        except Exception as e:
            self.display_message(f"Erro ao enviar mensagem: {e}")

    def send_message_thread(self, message, destination):
        #Função para enviar a mensagem em uma thread separada.
        try:
        #Envia a mensagem para o servidor
            with self.lock:
                response = self.send_server.send_message(self.username, self.room_name, message, destination)
            self.display_message(f"Você: {message}")
            self.message_entry.delete(0, tk.END)  #Limpa o campo de input

        except Exception as e:
            self.display_message(f"Erro ao enviar mensagem: {e}")

    def start_message_thread(self):
        #Inicia uma thread para buscar mensagens periodicamente.
        threading.Thread(target=self.check_messages, daemon=True).start()

    def check_messages(self):
        #Verifica e exibe novas mensagens periodicamente.
        while self.running:
            try:
                server = get_server_proxy("send_message")
                messages = server.receive_messages(self.username, self.room_name)
                #Verifica se as mensagens já foram exibidas
                new_messages = [msg for msg in messages if msg["timestamp"] not in self.displayed_messages] #procura apenas mensagens novas
                #Exibe as últimas 50 mensagens públicas
                for msg in new_messages[-50:]:
                    display_text = f"[{msg['timestamp']}] {msg['origin']} -> {msg['destination'] or 'Todos'}: {msg['content']}"
                    self.display_message(display_text)
                    self.displayed_messages.add(msg["timestamp"])

                server = get_server_proxy("list_users")
                users = server.list_users(self.room_name) #Obtem os usuários da sala
                    
                if users != self.current_users:
                    self.current_users = users
                    self.update_user_menu(users) #Atualiza o menu com os usuários

            except Exception as e:
                self.display_message(f"Erro ao buscar mensagens: {e}")
            time.sleep(2)  # Aguarda 2 segundos antes de verificar novamente

    def update_user_menu(self, users):
        #Atualiza a caixa de seleção de usuários.

        #Checa se existe um menu
        if not hasattr(self.user_menu, "menu") or self.user_menu["menu"] is None:
            return
        #Exclui o próprio usuário da lista
        users = [user for user in users if user != self.username]

        #Atualiza o menu com os usuários
        menu = self.user_menu["menu"]
        menu.delete(0, "end")  #Limpa as opções existentes
        menu.add_command(label="broadcast", command=tk._setit(self.user_var, "broadcast"))  #Adiciona a opção "broadcast"
        
        for user in users:
            menu.add_command(label=user, command=tk._setit(self.user_var, user))  #Adiciona os usuários

    def display_message(self, message):
        #Adiciona uma mensagem à área de chat.
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)  #Rola para a última mensagem

    def on_closing(self):
        #Função chamada quando o usuário tenta fechar a janela.
        self.running = False  # Desativa as threads
        # Remove o usuário da sala
        with self.lock:
            try:
                server = get_server_proxy("send_message")
                server.send_message(self.username, self.room_name, "!exit")

                # Fecha a janela
                self.root.destroy()
            except Exception as e:
                self.display_message(f"Erro ao enviar mensagem: {e}")
        self.root.after(100, self.root.destroy) #aguarda para fechata a janela

#Estado 1: Registro de Usuário
def registro():
    answer = None
    while answer == None or answer == "Este nome de usuário já existe.":
        username = input("Digite seu nome de usuário: ")
        server = get_server_proxy("register_user")
        if server is None:
            print("Procedimento 'register_user' não encontrado.")
            continue
        answer = server.register_user(username)
        print(answer)
    return username, "MENU_SALA"

#Estado 2: Menu para criar ou entrar em sala
def menu_sala(username):
    #Função para listar usuários
    def list_users_in_room(room_name):
        server = get_server_proxy("list_users")
        users = server.list_users(room_name)
        if users:
            print("Usuários na sala:")
            for user in users:
                print(f"- {user}")
        else:
            print("Nenhum usuário na sala.")

    print(f"\n{username}, o que deseja?:\n1. Criar Sala\n2. Entrar em uma Sala\n3. Desconectar")
    choice = input("Escolha uma opção: ")

    if choice == "1":
        room_name = input("Digite o nome da nova sala: ")
        server = get_server_proxy("create_room")
        room_creation = server.create_room(room_name) #Criação da sala
        print(room_creation.get("msg"))
        if room_creation.get("status"):
            server = get_server_proxy("join_room")
            response = server.join_room(username, room_name)
            list_users_in_room(room_name) #Listar usuários na sala
            messages = response.get("messages", [])
            if not messages:          
                print("Nenhuma mensagem recente.\n")
            return username, room_name, "NA_SALA"
        else:
            return username, room_name, "MENU_SALA"

    elif choice == "2":
        server = get_server_proxy("list_rooms")
        room_list = server.list_rooms()
        if room_list:
            print("\nSalas Disponíveis:")
            print(f"\n{room_list}") #Lista as salas 
            room_name = input("\nDigite o nome da sala: ")
            if room_name in room_list:
                server = get_server_proxy("join_room")
                response = server.join_room(username, room_name)
                list_users_in_room(room_name) #Listar usuários na sala
                messages = response.get("messages", [])
                if not messages:
                    print("Nenhuma mensagem recente.\n")
                return username, room_name, "NA_SALA" #Vai para o estado NA SALA
            else:
                print("Esta sala não existe.")
                return username, None, "MENU_SALA"

        else:
            print("Não há salas criadas.")
            return username, None, "MENU_SALA"

    elif choice == "3":
        return username, None, "DESCONEXAO"

#Estado 3: Usuário na sala
def na_sala(username, room_name):

    return username, room_name, "MENU_SALA"


def main():           
    state = "REGISTRO" #Estado Inicial
    username = None
    room_name = None

    #Máquina de estados
    while True:
        if state == "REGISTRO":
            username, state = registro()
        elif state == "MENU_SALA":
            username, room_name, state = menu_sala(username)
        elif state == "NA_SALA":
            root = tk.Tk()
            ChatClient(root, username, room_name)
            root.mainloop()
            username, room_name, state = na_sala(username, room_name)
        elif state == "DESCONEXAO":
            print("Usuário desconectado. Retornando ao registro...")
            state = "REGISTRO"

    #Criar fluxo
    #Registro usuário -> criar sala ou entrar em sala -> mandar e receber mensagens

if __name__ == "__main__":
    main()