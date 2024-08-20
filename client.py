import os.path
import socket
import re
import json

HEADER = 64
PORT = 20021
LENGTH = 1000000
SERVER = "127.0.1.1"
FORMAT = 'utf-8'
ADDRESS = (SERVER, PORT)

FULL_DIR_CODE = "150"
QUIT_CODE = "523"
SEND_OK_CODE = "150"

def connector(addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(addr)
    return sock


client = connector(ADDRESS)


def send(msg):
    json_str = command_chooser(msg)

    message = json_str.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    client.send(send_length)
    client.send(message)

    server_response_json = client.recv(2048).decode(FORMAT)
    server_response = json.loads(server_response_json)

    status_code = server_response["StatusCode"]
    description = server_response["Description"]
    print(f"{status_code} {description}")
    if status_code == SEND_OK_CODE:
        if msg[:2] == "ls":
            data_socket = data_connector(server_response)
            list_length = int(data_socket.recv(2048).decode(FORMAT))
            for i in range(list_length):
                file_name = data_socket.recv(2048).decode(FORMAT)
                print(file_name)
            server_ack_json = data_socket.recv(2048).decode(FORMAT)
            server_ack = json.loads(server_ack_json)
            ack_code = server_ack["StatusCode"]
            ack_description = server_ack["Description"]
            print(f"{ack_code} {ack_description}")

        if msg[:3] == "get":
            data_socket = data_connector(server_response)
            _, file_name = re.split(r"\s+", msg, maxsplit=2)
            file_data = data_socket.recv(2048)
            with open(file_name, 'wb') as file:
                file.write(file_data)
            server_ack_json = data_socket.recv(2048).decode(FORMAT)
            server_ack = json.loads(server_ack_json)
            ack_code = server_ack["StatusCode"]
            ack_description = server_ack["Description"]
            print(f"{ack_code} {ack_description}")

        if msg[:3] == "put":
            data_socket = data_connector(server_response)
            _, file_name = re.split(r"\s+", msg, maxsplit=2)
            file_path = get_path() + "/" + file_name
            with open(file_path, 'rb') as file:
                file_data = file.read()
            data_socket.sendall(file_data)
            server_ack_json = data_socket.recv(LENGTH).decode(FORMAT)
            server_ack = json.loads(server_ack_json)
            ack_code = server_ack["StatusCode"]
            ack_description = server_ack["Description"]
            print(f"{ack_code} {ack_description}")

        if msg[:4] == "mput":
            data_socket = data_connector(server_response)
            file_name_list = re.split(r"\s+", msg)
            for file_name in file_name_list:
                if file_name == "mput":
                    continue
                file_path = get_path() + "/" + file_name
                with open(file_path, 'rb') as file:
                    file_data = file.read()
                data_socket.sendall(file_data)
                server_ack_json = data_socket.recv(LENGTH).decode(FORMAT)
                print("json:",server_ack_json)
                server_ack = json.loads(server_ack_json)
                ack_code = server_ack["StatusCode"]
                ack_description = server_ack["Description"]
                print(f"{ack_code} {ack_description}")

    return status_code != QUIT_CODE


def data_connector(response):
    new_port = int(response["DataPort"])
    return connector((SERVER, new_port))


def command_chooser(cmd):
    if cmd[:3] == "ath":
        try:
            _, user, password = re.split(r"\s+", cmd, maxsplit=3)
        except:
            return json.dumps({"Cmd": "NONE"})
        if (user != "") and (password != ""):
            return json.dumps({"Cmd": "AUTH", "User": user, "Password": password})

    if cmd[:4] == "quit":
        return json.dumps({"Cmd": "QUIT"})

    if cmd[:2] == "ls":
        return json.dumps({"Cmd": "LIST"})

    if cmd[:3] == "get":
        try:
            _, file_name = re.split(r"\s+", cmd, maxsplit=2)
        except:
            return json.dumps({"Cmd": "NONE"})
        if file_name != "":
            return json.dumps({"Cmd": "GET", "FileName": file_name})

    if cmd[:3] == "put":
        try:
            _, file_name = re.split(r"\s+", cmd, maxsplit=2)
        except:
            return json.dumps({"Cmd": "NONE"})

        file_names = list_enquirer()
        if (file_name != "") and (file_name in file_names):
            return json.dumps({"Cmd": "PUT", "FileName": file_name})
        elif file_name not in file_names:
            print("File doesn't exist")

    if cmd[:4] == "mput":
        try:
            file_name_list = re.split(r"\s+", cmd)
        except:
            return json.dumps({"Cmd": "NONE"})

        message_dict = {}
        i = 1
        for name in file_name_list:
            file_names = list_enquirer()
            if (name != "mput") and ((name == "") or (name not in file_names)):
                print("file doesn't exist")
                return json.dumps({"Cmd": "NONE"})
            if name != "mput":
                message_dict.update({f"FileName_{i}": name})
                i += 1
            else:
                message_dict.update({"Cmd": "MPUT"})

        return json.dumps(message_dict)




    if cmd[:6] == "delete":
        try:
            _, file_name = re.split(r"\s+", cmd, maxsplit=2)
        except:
            return json.dumps({"Cmd": "NONE"})

        if file_name != "":
            return json.dumps({"Cmd": "DELE", "FileName": file_name})

    return json.dumps({"Cmd": "NONE"})


def get_path():
    return os.path.dirname(os.path.abspath(__file__))


def list_enquirer():
    path = get_path()
    directory = os.listdir(path)
    return directory


connected = True
while connected:
    connected = send(input())
