from typing import Callable

import threading as Threading
import socket as Socket

class PortManager:

    def __init__(self, ip : str, port : int):
        self.__ip = ip
        self.__port = port
        self.__connections = []

        self.__defined_socket = Socket.socket(Socket.AF_INET, Socket.SOCK_STREAM)
        
        return
    
    def __start_loop(self, function):
        d_socket = self.__defined_socket
        while self.__running:
            connection, address = d_socket.accept()
            print("[+] ", address)
            self.__connections.append(connection)
            
            thread = Threading.Thread(target=self.__handle_client, args=(d_socket, address, function), daemon=True)
            thread.start()

            continue
        return

    def __handle_client(self, client_socket: Socket.socket, address: tuple, function : Callable):
        with client_socket:
            while self.__running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    function(data.decode('utf-8'), address)
                except:
                    break
        
        if client_socket in self.__connections:
            self.__connections.remove(client_socket)
        print(f"[-] {address}")
        

    def listenPort(self, function : Callable) -> None:
        d_socket = self.__defined_socket
        
        d_socket.bind((self.__ip, self.__port))
        d_socket.listen(1)
        self.__running = True

        thread = Threading.Thread(target=self.__start_loop, args=(function), daemon=True)
        thread.start()
        
    def closeConnections(self) -> bool:
        self.__running = False
        try:
            for conn in self.__connections: conn.close()
            return True
        except Exception:
            return False
    
    def callPort(self, data : any) -> any:
        client_socket = Socket.socket(Socket.AF_INET, Socket.SOCK_STREAM)
        client_socket.connect((self.__ip, self.__port))
        client_socket.send(data.encode('utf-8'))
        response = client_socket.recv(1024)
        client_socket.close()
        return response
