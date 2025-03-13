import socket
import threading
import time
import hashlib
import sys
import requests
import json

# Configurações do servidor
HOST = '127.0.0.1'      
PORT = 31471             
WINDOW_SIZE = 1000000    
TIMEOUT = 60             # inatividade do cliente

# Estruturas de dados para gerenciar transações e clientes
pending_transactions = []     
validated_transactions = []   
clients = {}                  # Informações sobre os clientes conectados
lock = threading.Lock()       # Lock para sincronização de threads
shutdown_flag = False         # Flag para indicar que o servidor deve ser encerrado
next_transaction_id = 1       # Contador global para o número da transação

# Configurações do Telegram
TOKEN = 'SEUTOKENAQUI'
URL = f"https://api.telegram.org/bot{TOKEN}"
telegram_users = set()             # Conjunto de usuários do Telegram
telegram_users_to_ignore = set()   # Usuários do Telegram a serem ignorados temporariamente

# Função para obter atualizações do Telegram
def request_telegram():
    id_update = 0
    while not shutdown_flag:
        try:
            response = requests.get(URL + f"/getUpdates?offset={id_update}")
            dados = response.json()
            for info in dados["result"]:
                chat_id = info["message"]["chat"]["id"]
                usuario = info["message"]["from"].get("first_name", "") + " " + info["message"]["from"].get("last_name", "")
                mensagem_telegram = info["message"].get("text", "")
                # Se o chat ainda não foi registrado, adiciona-o ao conjunto de usuários.
                if chat_id not in telegram_users:
                    telegram_users.add(chat_id)

                if mensagem_telegram:
                    print(f"{usuario} enviou: {mensagem_telegram}")
                    telegram_users_to_ignore.add(chat_id)  # Ignora mensagens futuras deste usuário (se necessário)
                    handle_telegram_command(chat_id, mensagem_telegram)
                    # Processa o comando recebido via Telegram.
                id_update = info["update_id"] + 1
        except Exception as e:
            print(f"Erro ao obter mensagens do Telegram: {e}")
        time.sleep(10)

# Função para lidar com comandos do Telegram
def handle_telegram_command(chat_id, command):
    if command == "/validtrans":
        with lock:
            if validated_transactions:  # Monta uma lista de transações validadas formatadas.
                response = "\n".join(
                    [f"Transação: {trans['num_transacao']}, Nonce: {trans['nonce']}, Validado por: {trans['client_id']}"
                     for trans in validated_transactions])
            else:
                response = "Nenhuma transação validada."
        send_message_to_telegram(chat_id, response)
    elif command == "/pendtrans":
        with lock:
            if pending_transactions: # Monta uma lista de transações pendentes de validação.
                response = "\n".join(
                    [f"Transação: {trans['num_transacao']}, Bits: {trans['bits_zero']}, Clientes validando: {trans['num_cliente']}"
                     for trans in pending_transactions])
            else:
                response = "Nenhuma transação pendente."
        send_message_to_telegram(chat_id, response)
    elif command == "/clients":
        with lock:
            if clients: # Lista os clientes conectados e as transações que estão validando.
                response = "\n".join(
                    [f"Cliente: {info['nome']}, Transação: {info['current_transaction']}, Janela: {info['window_start']}-{info['window_start'] + WINDOW_SIZE}"
                     for client_id, info in clients.items()])
            else:
                response = "Nenhum cliente conectado."
        send_message_to_telegram(chat_id, response)
    elif command == "/help":
        help_text = """
        Comandos disponíveis:
/validtrans - Lista as transações validadas.
/pendtrans - Lista as transações pendentes de validação.
/clients - Lista os clientes conectados e suas transações atuais.
/help - Exibe esta mensagem de ajuda.
    """
        send_message_to_telegram(chat_id, help_text)
    elif command == "/start":
        start_text = """
    Seja bem-vindo ao Bot ovo podre,
ao executar o comando /help será
direcionado ao menu contendo 
todas as opções do Bot :)
    """
        send_message_to_telegram(chat_id, start_text)
    else: # Caso o comando não seja reconhecido, informa ao usuário.
        error_message = "Comando não reconhecido. Use /help para ver a lista de comandos disponíveis."
        send_message_to_telegram(chat_id, error_message)

# Função para enviar mensagens pelo Telegram
def send_message_to_telegram(chat_id, text):
    try:
        params = {'chat_id': chat_id, 'text': text}
        requests.get(URL + "/sendMessage", params=params)
        print(f"Enviando para Telegram ID {chat_id}: {text}")
    except Exception as e:
        print(f"Erro ao enviar para Telegram ID {chat_id}: {e}")

# Função principal para lidar com cada cliente
def handle_client(conn, addr):
    print(f"Novo cliente conectado: {addr}")
    try:
        # Recebe o nome do cliente (10 bytes)
        nome = conn.recv(10).decode('utf-8').strip()
        
        print(f"Cliente {addr} se identificou como: {nome}")
    except Exception as e:
        print(f"Erro ao receber nome do cliente {addr}: {e}")
        conn.close()
        return

    client_id = addr[1]  # Usamos a porta do cliente como ID
    with lock:
        clients[client_id] = {
            "conn": conn,
            "nome": nome,  # Armazena o nome do cliente
            "last_request": time.time(),  # Última requisição 
            "current_transaction": None,  # Transação que o cliente está validando
            "window_start": 0            # Início da janela 
        }

    while not shutdown_flag:
        try:
            data = conn.recv(1024)
            if not data:
                break
            with lock: #evitar condições de corrida entre as threads
                #atualiza o tempo da ultima atv do cliente
                clients[client_id]["last_request"] = time.time()
            msg_type = data[0:1]
            if msg_type == b"G":
                handle_get_work(conn, client_id)
            elif msg_type == b"S":
                if len(data) < 7:  # Verifica se o pacote tem o tamanho mínimo esperado
                    conn.send("Pacote inválido".encode('utf-8'))
                    continue
                handle_submit_nonce(conn, client_id, data) #processa o nonce validado
            else:
                conn.send("Comando inválido".encode('utf-8'))
        except socket.error as e:
            print(f"Erro de socket ao lidar com o cliente {addr}: {e}")
            break
        except Exception as e:
            print(f"Erro ao lidar com o cliente {addr}: {e}")
            break

    with lock:
        if client_id in clients:
            del clients[client_id] # Remove o cliente da lista de clientes conectados
    conn.close() #fecha conec com clientes
    print(f"Conexão encerrada com {addr}")

# Função para enviar uma transação ao cliente
def handle_get_work(conn, client_id):
    with lock:
        if pending_transactions:
            transaction = pending_transactions[0]
            num_cliente = transaction["num_cliente"]
            window_start = num_cliente * WINDOW_SIZE  # Janela do cliente baseado no número de clientes já conectados
            clients[client_id]["current_transaction"] = transaction["num_transacao"]
            clients[client_id]["window_start"] = window_start
            transaction["num_cliente"] += 1  # Incrementa o número de clientes
            trans_bytes = transaction["transacao"].encode('utf-8')

            response = (
                b"T" +  # b"T" -> indicador de transação,
                transaction["num_transacao"].to_bytes(2, byteorder='big') + #2 byte
                num_cliente.to_bytes(2, byteorder='big') + #2 byte
                WINDOW_SIZE.to_bytes(4, byteorder='big') + #4 byte
                transaction["bits_zero"].to_bytes(1, byteorder='big') + #1 byte
                len(trans_bytes).to_bytes(4, byteorder='big') + #4 byte
                trans_bytes
            )
            conn.send(response)
        else:
            conn.send(b"W") # Indica que não há transações pendentes

# Função para processar um nonce enviado pelo cliente
def handle_submit_nonce(conn, client_id, data):
    if len(data) < 7:
        return  # Se o pacote for menor que o esperado, não presta.
    try:
        num_transacao = int.from_bytes(data[1:3], byteorder='big')
        nonce = int.from_bytes(data[3:7], byteorder='big')
    except ValueError as e:
        conn.send("Nonce ou número de transação inválido".encode('utf-8'))
        return

    with lock:
        # Procura a transação pendente que corresponde ao número recebido.
        transaction = next((t for t in pending_transactions if t["num_transacao"] == num_transacao), None)
        if transaction:
            n_by = nonce.to_bytes(4, byteorder='big')
            hash_result = hashlib.sha256(n_by + transaction["transacao"].encode('utf-8')).hexdigest()
            target = (1 << (256 - transaction["bits_zero"])) - 1
            if int(hash_result, 16) <= target:
                validated_transactions.append({
                    "num_transacao": num_transacao,
                    "nonce": nonce,
                    "client_id": clients[client_id]["nome"]  # Usa o nome do cliente
                })
                # Remove a transação da lista de pendentes.
                pending_transactions[:] = [t for t in pending_transactions if t["num_transacao"] != num_transacao]
                print(f"Transação {num_transacao} validada com nonce {nonce} pelo cliente {clients[client_id]['nome']}")
                conn.send(b"V" + num_transacao.to_bytes(2, byteorder='big'))
                # Notifica os demais clientes que estão trabalhando na mesma transação
                for c_id, info in clients.items():
                    if c_id != client_id and info["current_transaction"] == num_transacao:
                        info["conn"].send(b"I" + num_transacao.to_bytes(2, byteorder='big'))
            else:
                conn.send(b"R" + num_transacao.to_bytes(2, byteorder='big')) #Rejeita se nao cumprir os criterios
        else:
            conn.send(b"R" + num_transacao.to_bytes(2, byteorder='big')) #Mesma coisa so que com a transação

# Função para adicionar uma nova transação manualmente
def add_transaction():
    global next_transaction_id
    transacao = input("Informe a transação: ") 
    bits_zero = input("Informe a quantidade de bits iniciais em zero: ")
    if not bits_zero.isdigit():
        print("Quantidade de bits inválida. Deve ser um número inteiro.")
        return
    bits_zero = int(bits_zero)
    with lock:
        num_transacao = next_transaction_id # Atribui um número único à transação.
        next_transaction_id += 1 # Incrementa o contador global.
         # Adiciona a transação na lista de pendentes
        pending_transactions.append({
            "num_transacao": num_transacao,
            "transacao": transacao,
            "bits_zero": bits_zero,
            "num_cliente": 0
        })
        print(f"Transação {num_transacao} adicionada: {transacao}")

# Função para listar transações validadas
def list_validated_transactions():
    with lock:
        if len(validated_transactions) == 0:
            print("Nenhuma transação validada")
        for trans in validated_transactions:
            print(f"Transação: {trans['num_transacao']}, Nonce: {trans['nonce']}, Validado por: {trans['client_id']}")

# Função para listar transações pendentes
def list_pending_transactions():
    with lock:
        for trans in pending_transactions:
            print(f"Transação: {trans['num_transacao']}, Bits: {trans['bits_zero']}, Clientes validando: {trans['num_cliente']}")

# Função para listar clientes conectados
def list_clients():
    with lock:
        if len(clients) == 0:
            print("não ha clientes")
        for client_id, info in clients.items():
            print(f"Cliente: {info['nome']}, Transação: {info['current_transaction']}, Janela: {info['window_start']}-{info['window_start'] + WINDOW_SIZE}")

# Função para verificar timeouts dos clientes
def check_timeouts():
    while not shutdown_flag:
        time.sleep(10)
        with lock:
            current_time = time.time()
            # Cria uma cópia dos clientes (para que nao seja alterado o dicionario durante a execusão do codigo)
            for client_id, info in list(clients.items()): # Dados associados ao cliente
                if current_time - info["last_request"] > TIMEOUT: #verifica a diferença de tempo com a ultima requisição
                    print(f"Cliente {client_id} desconectado por timeout")
                    try:
                        info["conn"].send(b"Q")  # Notifica o cliente de encerramento
                        info["conn"].close()
                    except Exception as e:
                        print(f"Erro ao desconectar cliente {client_id}: {e}")
                    del clients[client_id]  # Por fim, Remove o cliente da lista.

# Função para encerrar o servidor
def shutdown_server():
    global shutdown_flag
    with lock:
        for client_id, info in clients.items():
            try:
                info["conn"].send(b"Q")
                time.sleep(1)  # Aguarda o cliente processar a mensagem
                info["conn"].close()
            except Exception as e:
                print(f"Erro ao encerrar conexão com o cliente {client_id}: {e}")
        shutdown_flag = True
    print("Servidor encerrado.")
    sys.exit(0)

# Função para exibir os comandos disponíveis
def show_help():
    print("\nComandos disponíveis:")
    print("/newtrans - Adiciona uma nova transação para validação.")
    print("/validtrans - Lista as transações validadas.")
    print("/pendtrans - Lista as transações pendentes de validação.")
    print("/clients - Lista os clientes conectados e suas transações atuais.")
    print("/quit - Encerra o servidor e notifica os clientes.")
    print("/help - Exibe esta mensagem de ajuda.\n")

# Função para comandos do servidor (terminal)
def server_commands():
    print("Use o comando /help para verificar os comandos disponíveis.")
    while True:
        command = input()
        if command == "/newtrans":
            add_transaction()
        elif command == "/validtrans":
            list_validated_transactions()
        elif command == "/pendtrans":
            list_pending_transactions()
        elif command == "/clients":
            list_clients()
        elif command == "/quit":
            shutdown_server()
        elif command == "/help":
            show_help()
        else:
            print("Comando inválido. Use /help para ver os comandos disponíveis.")

# Função principal do servidor
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor iniciado em {HOST}:{PORT}")

         # Cria threads daemon (SP)
        command_thread = threading.Thread(target=server_commands, daemon=True)
        timeout_thread = threading.Thread(target=check_timeouts, daemon=True)
        telegram_thread = threading.Thread(target=request_telegram, daemon=True)

        # Inicia as threads
        command_thread.start()
        timeout_thread.start()
        telegram_thread.start()

        while not shutdown_flag:
            try:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr)).start()
            except Exception as e:
                if shutdown_flag:
                    break
                print(f"Erro ao aceitar conexão: {e}")

        # Aguarda o término das threads
        command_thread.join()
        timeout_thread.join()
        telegram_thread.join()

start_server()