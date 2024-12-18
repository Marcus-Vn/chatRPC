from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from datetime import datetime


rooms = {}  # Armazena salas
users = {}  # Armazena usuários registrados

#método para registrar um usuário
def register_user(username):
    if username in users:
        return "Este nome de usuário já existe."
    users[username] = None  # Usuário não está em nenhuma sala
    return f"Usuário {username} registrado com sucesso."

#método para criar uma sala
def create_room(room_name):
    if room_name in rooms:
        return {"status": False, "msg": "Esta sala já existe."}
    rooms[room_name] = {"messages": [], "users": []} #cria lista de msgs e usuarios
    return {"status": True, "msg": f"Sala {room_name} criada com sucesso."}

#método para entrar em uma sala
def join_room(username, room_name):
    if room_name not in rooms:
        return {"status": False, "msg": "Esta sala não existe."}
    if username not in users:
        return {"status": False, "msg": "Usuário não registrado."}
    rooms[room_name]["users"].append(username) #Adiciona usuário a sala
    users[username] = room_name

    # Adiciona mensagem ao histórico informando que o usuário entrou
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_message = {
        "type": "broadcast",
        "timestamp": timestamp,
        "origin": "Sistema",
        "destination": None,  # Mensagem para todos
        "content": f"{username} entrou na sala."
    }
    rooms[room_name]["messages"].append(new_message)
    

    messages = [
        f"[{message['timestamp']}] {message['origin']} -> {message['destination'] or 'All'}: {message['content']}"
        for message in rooms[room_name]["messages"][-50:]
        if message['destination'] is None or message['destination'] == username
    ]
    return {"messages": messages}
    

#Método para enviar as mensagens
def send_message(username, room_name, message, recipient=None):
    if room_name not in rooms:
        return "Esta sala não existe."
    if username not in rooms[room_name]["users"]:
        return "Usuário não está na sala."
    if message == "!exit":
        rooms[room_name]["users"].remove(username)
        message = f"{username} saiu da sala."
        username = "Sistema" #Mensagem de saída, enviada pelo Sistema
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = {
        "type": "unicast" if recipient else "broadcast",
        "origin": username,
        "content": message,
        "destination": recipient,
        "timestamp": timestamp
    }
    rooms[room_name]["messages"].append(msg) #Adiciona mensagem ao histórico
    return "Mensagem enviada."

#Método para receber as mensagens
def receive_messages(username, room_name):
    if room_name not in rooms:
        return {"error": f"Sala '{room_name}' não existe."}
    
    if username not in rooms[room_name]["users"]:
        return {"error": f"Usário '{username}' não está na sala '{room_name}'."}
    
    # Filtra mensagens relevantes (broadcast ou destinadas ao usuário)
    relevant_messages = [
        message for message in rooms[room_name]["messages"]
        if message["origin"] != username and (message["destination"] is None 
        or message["destination"] == username)
    ]
    
    return relevant_messages

#Método para listar salas
def list_rooms():
    room_list = list(rooms.keys())
    if room_list:
        return room_list
    else:
        return False

#Método para listar usuários
def list_users(room_name):
    if room_name not in rooms:
        return "A sala não existe."
    return rooms[room_name]["users"]

def main():
    #Cria o Server
    server_port = 8000
    server = SimpleXMLRPCServer(("localhost", server_port), allow_none=True)

    #Registra métodos no Server
    server.register_function(register_user, "register_user")
    server.register_function(create_room, "create_room")
    server.register_function(join_room, "join_room")
    server.register_function(send_message, "send_message")
    server.register_function(receive_messages, "receive_messages")
    server.register_function(list_rooms, "list_rooms")
    server.register_function(list_users, "list_users")

    #Registrar os procedimentos no Binder
    binder = ServerProxy('http://localhost:5000')
    binder.register_procedure("register_user", "localhost", server_port)
    binder.register_procedure("create_room", "localhost", server_port)
    binder.register_procedure("join_room", "localhost", server_port)
    binder.register_procedure("send_message", "localhost", server_port)
    binder.register_procedure("receive_messages", "localhost", server_port)
    binder.register_procedure("list_rooms", "localhost", server_port)
    binder.register_procedure("list_users", "localhost", server_port)

    print("Chat Server rodando na porta 8000...")
    server.serve_forever() #Mantém o servidor

if __name__ == "__main__":
    main()