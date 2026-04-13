from typing import Callable, List, Tuple, Any
import threading as Threading
import socket as Socket

class PortManager:
    """
    Gerencia conexões de rede em um socket específico.

    Esta classe encapsula a lógica de criação de um servidor TCP que escuta 
    múltiplas conexões em threads separadas, e também permite atuar como um 
    cliente para enviar dados para a mesma porta.
    """

    def __init__(self, ip: str, port: int) -> None:
        """
        Inicializa o PortManager com o IP e porta especificados.

        Args:
            ip (str): O endereço IP (IPv4) no qual o gerenciador será vinculado 
                (ex: '127.0.0.1' ou '0.0.0.0').
            port (int): O número da porta para escutar ou conectar.
        """
        self.__ip: str = ip
        self.__port: int = port
        self.__connections: List[Socket.socket] = []
        self.__running: bool = False
        self.__defined_socket: Socket.socket = Socket.socket(Socket.AF_INET, Socket.SOCK_STREAM)

    def __start_loop(self, function: Callable[[str, Tuple[str, int]], Any]) -> None:
        """
        Inicia o loop principal de aceitação de conexões.

        Args:
            function (Callable): A função de callback a ser passada para cada cliente.
        """
        d_socket = self.__defined_socket
        while self.__running:
            try:
                connection, address = d_socket.accept()
                print(f"[+] Conexão recebida de: {address}")
                self.__connections.append(connection)
                
                thread = Threading.Thread(
                    target=self.__handle_client, 
                    args=(connection, address, function), 
                    daemon=True
                )
                thread.start()
            except Exception as e:
                if self.__running:
                    print(f"Erro ao aceitar conexão: {e}")
                break

    def __handle_client(self, client_socket: Socket.socket, address: Tuple[str, int], function: Callable[[str, Tuple[str, int]], Any]) -> None:
        with client_socket:
            while self.__running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    response = function(data.decode('utf-8'), address)
                    if response is None:
                        continue
                    if isinstance(response, bytes):
                        safe_data = response
                    elif isinstance(response, str):
                        safe_data = response.encode('utf-8')
                    else:
                        safe_data = json.dumps(response).encode('utf-8')

                    client_socket.sendall(safe_data)

                except Exception as e:
                    print(f"Erro na conexão com {address}: {e}")
                    break
        
        if client_socket in self.__connections:
            self.__connections.remove(client_socket)
        print(f"[-] Conexão encerrada com: {address}")

    def listenPort(self, function: Callable[[str, Tuple[str, int]], Any]) -> None:
        """
        Inicia um servidor TCP que escuta ativamente por conexões de entrada.

        Este método não bloqueia a thread principal. Ele inicia uma nova thread 
        em background que aceitará conexões e distribuirá cada cliente para 
        sua própria thread de processamento.

        Args:
            function (Callable[[str, Tuple[str, int]], Any]): Um callback que 
                será executado toda vez que o servidor receber dados. Deve aceitar 
                uma string (dados) e uma tupla (IP e Porta).

        Raises:
            OSError: Se a porta já estiver em uso ou o IP for inválido.

        Examples:
            >>> def meu_callback(dados: str, endereco: tuple):
            ...     print(f"Recebido {dados} de {endereco}")
            ...
            >>> manager = PortManager('127.0.0.1', 8080)
            >>> manager.listenPort(meu_callback)
        """
        d_socket = self.__defined_socket
        
        d_socket.bind((self.__ip, self.__port))
        d_socket.listen(5) # Modificado para permitir uma fila maior
        self.__running = True
        
        thread = Threading.Thread(target=self.__start_loop, args=(function,), daemon=True)
        thread.start()
        
    def closeConnections(self) -> bool:
        """
        Encerra todas as conexões ativas de clientes e desliga o servidor de escuta.

        Returns:
            bool: Retorna True se o encerramento ocorreu com sucesso. Retorna False
                se ocorreu alguma exceção durante o processo.

        Examples:
            >>> manager.closeConnections()
            True
        """
        self.__running = False
        try:
            for conn in self.__connections: 
                conn.close()
            self.__connections.clear()
            self.__defined_socket.close()
            return True
        except Exception:
            return False
    
    def callPort(self, data: str) -> bytes:
        """
        Conecta-se ao IP e porta configurados, envia os dados e aguarda resposta.

        Atua como um cliente TCP pontual. Ele abre uma conexão, envia os dados 
        codificados em UTF-8, espera uma resposta (até 1024 bytes) e fecha a conexão.

        Args:
            data (str): A mensagem em formato de texto a ser enviada ao servidor.

        Returns:
            bytes: A resposta crua (em bytes) recebida do servidor. 
                Pode ser decodificada com `.decode('utf-8')` se for texto.

        Raises:
            ConnectionRefusedError: Se o servidor de destino não estiver escutando.
            TimeoutError: Se o servidor demorar demais para responder.

        Examples:
            >>> manager = PortManager('127.0.0.1', 8080)
            >>> resposta = manager.callPort("Olá Servidor!")
            >>> print(resposta.decode('utf-8'))
        """
        client_socket = Socket.socket(Socket.AF_INET, Socket.SOCK_STREAM)
        try:
            client_socket.connect((self.__ip, self.__port))
            client_socket.send(data.encode('utf-8'))
            response = client_socket.recv(1024)
            return response
        finally:
            client_socket.close()