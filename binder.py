from xmlrpc.server import SimpleXMLRPCServer

#Binder para gerenciar os procedimentos remotos
registry = {}  # Armazena os métodos registrados

#Método para registar os procedimentos
def register_procedure(procedure_name, address, port):
    #Verifica se o procedimento já está registrado
    if procedure_name in registry:
        return f"Procedimento {procedure_name} já registrado."
    registry[procedure_name] = (address, port)
    return f"Procedimento {procedure_name} registrado com sucesso."

#Método para descobrir endereço de procedimento pelo nome
def lookup_procedure(procedure_name):
    return registry.get(procedure_name, None)

if __name__ == "__main__":
    # Cria o servidor RPC para o binder
    server = SimpleXMLRPCServer(("localhost", 5000), allow_none=True)
    # Registra as funções
    server.register_function(register_procedure, "register_procedure")
    server.register_function(lookup_procedure, "lookup_procedure")
    print("Binder pronto e aguardando serviços...")

    # Mantém o servidor em execução
    server.serve_forever()