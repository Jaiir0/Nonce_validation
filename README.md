# Projeto de Validação de Nonce com Integração ao Telegram

Este projeto é uma implementação de um sistema de validação de Nonce, onde clientes conectados a um servidor central trabalham para encontrar um Nonce que, quando combinado com uma transação, gere um hash SHA256 que atenda a um critério específico (número de bits iniciais em zero). O sistema também integra um bot do Telegram para monitoramento e controle remoto.
Funcionalidades:

Servidor

    Gerenciamento de Clientes: Aceita conexões de múltiplos clientes, atribui tarefas de validação e gerencia timeouts.

    Transações: Adiciona novas transações para validação, gerencia transações pendentes e validadas.

    Comunicação com Clientes: Envia transações para validação e recebe Nonces encontrados pelos clientes.

    Integração com Telegram: Permite monitorar e controlar o servidor via comandos enviados por um bot do Telegram.

Cliente

    Conexão ao Servidor: Conecta-se ao servidor e recebe tarefas de validação.

    Validação de Nonce: Encontra um Nonce que, combinado com a transação, gere um hash SHA256 que atenda ao critério de bits iniciais em zero.

    Submissão de Nonce: Envia o Nonce encontrado de volta ao servidor para validação.

Bot do Telegram

    Comandos Disponíveis:

        /validtrans: Lista as transações validadas.

        /pendtrans: Lista as transações pendentes de validação.

        /clients: Lista os clientes conectados e suas transações atuais.

        /help: Exibe a lista de comandos disponíveis.

        /start: Mensagem de boas-vindas e instruções iniciais.

#Como Executar

Pré-requisitos

    Python 3.x

    Biblioteca requests para integração com o Telegram (pip install requests)

Configuração

    Servidor:

        Configure o endereço IP e a porta do servidor no arquivo server.py.

        Insira o token do bot do Telegram na variável TOKEN.

    Cliente:

        Configure o endereço IP e a porta do servidor no arquivo client.py.

Execução

    Servidor:

        python server.py
        O servidor estará pronto para aceitar conexões de clientes e comandos do Telegram.

    Cliente:

        python client.py
        O cliente se conectará ao servidor e começará a receber tarefas de validação.

Comandos do Servidor (Terminal)

    /newtrans: Adiciona uma nova transação para validação.

    /validtrans: Lista as transações validadas.

    /pendtrans: Lista as transações pendentes de validação.

    /clients: Lista os clientes conectados e suas transações atuais.

    /quit: Encerra o servidor e os clientes.

    /help: Exibe a lista de comandos disponíveis.

Estrutura do Projeto

    server.py: Contém a lógica do servidor, incluindo gerenciamento de clientes, transações e integração com o Telegram.

    client.py: Contém a lógica do cliente, incluindo conexão ao servidor e validação de Nonce.

Exemplo de Uso

    Adicionar uma Transação:

        No terminal do servidor, digite:

        /newtrans
        Insira a transação e a quantidade de bits iniciais em zero.

    Monitorar Transações:

        No Telegram, envie o comando:

        /pendtrans
        O bot responderá com a lista de transações pendentes.

    Validar Transação:

        O cliente automaticamente receberá a transação e começará a procurar o Nonce.

        Quando encontrar, o Nonce será enviado ao servidor para validação.

    Verificar Transações Validadas:

        No Telegram, envie o comando:

        /validtrans
        O bot responderá com a lista de transações validadas.

Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests para melhorar o projeto.
Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

Nota: Este projeto foi desenvolvido como parte de um exercício educacional e pode ser expandido para incluir mais funcionalidades e melhorias.
