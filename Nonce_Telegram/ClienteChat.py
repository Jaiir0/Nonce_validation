import socket
import time
import hashlib

HOST = '127.0.0.1'  # Endereço do servidor
PORT = 31471        # Porta do servidor


def find_nonce(transaction, bits, window_start, window_size):
    target = (1 << (256 - bits)) - 1  # Calcula o alvo para o hash SHA256
    for nonce in range(window_start, window_start + window_size):
        n_by = nonce.to_bytes(4, byteorder='big')
        hash_result = hashlib.sha256(n_by + transaction.encode('utf-8')).hexdigest()
        if int(hash_result, 16) <= target:
            return nonce
    return None

def start_client():
    try:
        # Solicita o nome do cliente
        try:
            nome = input("Digite seu nome: ").strip()
            if not nome:
                print("Nome não pode ser vazio. Usando 'ClienteDesconhecido' como nome padrão.")
                nome = "Desconhecido"
        except KeyboardInterrupt:
            print("\nCtrl+C pressionado. Fechando o cliente")
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))

            # Envia o nome ao servidor (10 bytes, padded com espaços)
            s.send(nome.encode('utf-8').ljust(10, b' '))
            # Preenche a representação em bytes para ter exatamente 10 bytes ljust
            while True:
                try:
                    # Envia mensagem G: 'G'
                    s.send(b"G")
                    data = s.recv(1024)
                    if not data: #sem data F total
                        print("Conexão com o servidor foi fechada.")
                        break

                    msg_type = data[0:1] #Extrai o primeiro byte da mensagem 1 byte
                    if msg_type == b'W':
                        print("Nenhuma transação disponível. Aguardando...")
                        time.sleep(10)
                    elif msg_type == b'T':
                    
                        if len(data) < 14:
                            print("Mensagem T inválida")
                            continue
                        num_transacao = int.from_bytes(data[1:3], 'big') #2 byte
                        num_cliente = int.from_bytes(data[3:5], 'big') #2 byte
                        tam_janela = int.from_bytes(data[5:9], 'big') #4 byte
                        bits_zero = int.from_bytes(data[9:10], 'big') #1 byte
                        tam_transacao = int.from_bytes(data[10:14], 'big') #4 byte

                        if len(data) < 14 + tam_transacao:
                            print("Mensagem T incompleta")
                            continue

                        transacao = data[14:14+tam_transacao].decode('utf-8')
                        window_start = num_cliente * tam_janela
                        print(f"Validando transação {num_transacao}, Bits: {bits_zero}, Janela: {window_start}-{window_start+tam_janela}")
                        nonce = find_nonce(transacao, bits_zero, window_start, tam_janela) #encontrar um nonce que gere um hash compatível (chama nonce)
                        if nonce is not None:
                            print(f"Nonce encontrado: {nonce}")
                            # Envia mensagem S: 'S' + numTransação (2 bytes) + nonce (4 bytes)
                            msg_nonce = b"S" + num_transacao.to_bytes(2, 'big') + nonce.to_bytes(4, 'big')
                            s.send(msg_nonce)
                            response = s.recv(1024)
                            if response and response[0:1] == b'V':
                                print("Transação validada com sucesso!")
                            elif response and response[0:1] == b'R':
                                print("Nonce rejeitado.")
                        else:
                            print("Nonce não encontrado na janela fornecida.")
                    elif msg_type == b"Q":  # Comando de encerramento
                        print("Servidor solicitou encerramento.")
                        break
                    else:
                        print("Resposta inesperada do servidor.")
                except ConnectionResetError: #Tratamento de erro quando o servidor é forçado a encerrar
                    print("Conexão com o servidor foi encerrada")
                    break
                except Exception as e:
                    print(f"Erro durante a execução do cliente: {e}")
                    break
    except Exception as e:
        print(f"Erro ao conectar ao servidor: {e}")

start_client()