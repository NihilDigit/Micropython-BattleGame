import usocket as socket
import ubinascii
import hashlib
import random

# WebSocket数据帧相关常量
OP_TEXT = 0x01
OP_CLOSE = 0x08
MASK = 0x80
MASKBIT = 0x80

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=2333):
        self.host = host
        self.port = port
        self.clients = {}  # 使用字典存储客户端地址和对应的客户端套接字对象
        self.start_server()

    def start_server(self):
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        self.socket = socket.socket()
        self.socket.bind(addr)
        self.socket.listen(1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('WebSocket server started on ws://%s:%s' % (self.host, self.port))
        self.listen()

    def listen(self):
        while True:
            try:
                client, addr = self.socket.accept()
                self.clients[addr] = client  # 使用地址作为键,将客户端套接字对象存储在字典中
                print("Client connected from", addr)
                self.handle_client(client, addr)
            except KeyboardInterrupt:
                print("Server shutting down.")
                self.shutdown()
                break

    def handle_client(self, client, addr):
        try:
            self.handshake(client)
            print("Client connected from", addr)
            while True:
                data = client.recv(1024)
                if not data:
                    break
                self.parse_frame(data, client, addr)
        except OSError:
            pass
        finally:
            self.remove_client(addr)

    def parse_frame(self, data, client, addr):
        opcode, payload = self.decode_frame(data)
        if opcode == OP_TEXT:
            print("Received message from %s: %s" % (addr, payload.decode()))
            self.send_frame(client, payload, OP_TEXT)
        elif opcode == OP_CLOSE:
            print("Client closed connection from", addr)
            self.send_frame(client, None, OP_CLOSE)

    def remove_client(self, addr):
        if addr in self.clients:
            client = self.clients[addr]
            client.close()
            del self.clients[addr]  # 使用地址作为键从字典中删除客户端套接字对象
            print("Client disconnected from", addr)

    def shutdown(self):
        for addr, client in self.clients.items():
            self.remove_client(addr)
        self.socket.close()

    @staticmethod
    def handshake(client):
        stream = client.makefile("rwb")
        req = stream.readline()
        method, path, protocol = req.split(b" ")
        headers = {}
        while True:
            header = stream.readline()
            if not header or header == b"\r\n":
                break
            header = str(header, "utf-8").strip()
            if ":" in header:
                key, value = header.split(":", 1)
                headers[key] = value.strip()

        if method == b"GET" and "Upgrade" in headers and headers["Upgrade"].lower() == "websocket":
            response = WebSocketServer.create_handshake_response(headers)
            client.sendall(response.encode())
        else:
            raise OSError("Invalid WebSocket request")

    @staticmethod
    def create_handshake_response(headers):
        key = headers["Sec-WebSocket-Key"]
        accept_key = ubinascii.b2a_base64(hashlib.sha1(key.encode() + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()).strip().decode()
        response = "HTTP/1.1 101 Switching Protocols\r\n"
        response += "Upgrade: websocket\r\n"
        response += "Connection: Upgrade\r\n"
        response += "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key
        return response

    @staticmethod
    def decode_frame(data):
        byte1, byte2 = data[0], data[1]
        is_masked = bool(byte2 & MASKBIT)
        opcode = byte1 & 0x0f
        payload_len = byte2 & 0x7f

        if payload_len < 126:
            payload_start = 2
        elif payload_len == 126:
            payload_start = 4
        else:
            payload_start = 10

        if is_masked:
            mask = data[payload_start:payload_start + 4]
            payload_start += 4
        else:
            mask = None

        payload_end = payload_start + payload_len
        payload = data[payload_start:payload_end]

        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

        return opcode, payload

    @staticmethod
    def encode_frame(payload, opcode):
        frame = bytes([opcode | MASK])
        if payload:
            payload_len = len(payload)
            if payload_len < 126:
                frame += bytes([payload_len | MASKBIT])
            elif payload_len < 65536:
                frame += bytes([126 | MASKBIT, payload_len >> 8, payload_len & 0xff])
            else:
                frame += bytes([127 | MASKBIT]) + bytes.fromhex("%016x" % payload_len)
            mask = bytes(random.getrandbits(8) for _ in range(4))
            frame += mask
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            frame += payload
        return frame

    def send_frame(self, client, payload, opcode):
        frame = self.encode_frame(payload, opcode)
        client.sendall(frame)

    def broadcast_message(self, message):
        for client in self.clients.values():  # 遍历字典的值,即客户端套接字对象
            try:
                self.send_frame(client, message.encode(), OP_TEXT)
            except OSError:
                self.remove_client(client, None)

    def send_to_client(self, addr, message):
        if addr in self.clients:
            client = self.clients[addr]
            try:
                self.send_frame(client, message.encode(), OP_TEXT)
            except OSError:
                self.remove_client(addr)
        else:
            print(f"Client {addr} not found.")
