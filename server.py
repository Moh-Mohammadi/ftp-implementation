import json
import socket
import threading
import os

# General parameters
HEADER = 64
PORT = 20021
LENGTH = 10000
SERVER = socket.gethostbyname(socket.gethostname())
ADDRESS = (SERVER, PORT)
FORMAT = 'utf-8'

QUIT_CODE = "523"
INVALID_CODE = "532"
ROOT_SUCCESS_CODE = "230"
ROOT_FAILURE_CODE = "430"
EMPTY_DIR_CODE = "210"
LIST_ACK_CODE = "226"
SEND_OK_CODE = "150"
NON_EXISTENT_FILE_CODE = "550"
NO_ACCESS_CODE = "434"
DELETE_SUCCESS_CODE = "200"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDRESS)
data_socket = None

# Authentication information
root_users = {
    "Mamad": "Mamad-ali",
    "Ali": "LoveAlwaysWins"
}


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    root_access = False
    connected = True
    while connected:
        msg_length = conn.recv(HEADER).decode(FORMAT)
        if msg_length:
            msg_length = int(msg_length)
            msg = conn.recv(msg_length).decode(FORMAT)

            server_response = command_processor(msg, addr, root_access)

            status_code = json.loads(server_response)["StatusCode"]
            if status_code == QUIT_CODE:
                connected = False

            if status_code == ROOT_SUCCESS_CODE:
                root_access = True

            conn.send(server_response.encode(FORMAT))

            if status_code == SEND_OK_CODE:
                command_dict = json.loads(msg)
                command = command_dict["Cmd"]

                if command == "LIST":
                    data_conn, _ = data_socket.accept()
                    file_names = list_enquirer()
                    data_conn.send(str(len(file_names)).encode(FORMAT))
                    for file_name in file_names:
                        data_conn.send(file_name.encode(FORMAT))
                    data_conn.send(
                        (json.dumps({"StatusCode": LIST_ACK_CODE, "Description": " Directory send OK"})).encode(FORMAT))
                    data_conn.close()

                if command == "GET":
                    data_conn, _ = data_socket.accept()
                    file_name = command_dict["FileName"]
                    file_path = get_path() + "/" + file_name
                    with open(file_path, 'rb') as file:
                        file_data = file.read()
                    data_conn.sendall(file_data)
                    data_conn.send(
                        (json.dumps({"StatusCode": LIST_ACK_CODE, "Description": "Transfer Complete"})).encode(FORMAT))
                    data_conn.close()

                if command == "PUT":
                    data_conn, _ = data_socket.accept()
                    file_name = command_dict["FileName"]
                    file_data = data_conn.recv(LENGTH)
                    with open(file_name, 'wb') as file:
                        file.write(file_data)
                    data_conn.send(
                        (json.dumps({"StatusCode": LIST_ACK_CODE, "Description": "Transfer Complete"})).encode(FORMAT))
                    data_conn.close()

                if command == "MPUT":
                    data_conn, _ = data_socket.accept()
                    for i in range(1, len(command_dict) - 1):
                        file_name = command_dict[f"FileName_{i}"]
                        file_data = data_conn.recv(LENGTH)
                        with open(file_name, 'wb') as file:
                            file.write(file_data)
                        print(file_name)
                        data_conn.send(
                            (json.dumps({"StatusCode": LIST_ACK_CODE, "Description": "Transfer Complete",
                                         "FileName": file_name})).encode(FORMAT))

                    data_conn.close()

    conn.close()


def command_processor(msg, addr, root_access):
    cmd_dict = json.loads(msg)
    cmd = cmd_dict["Cmd"]

    if cmd == "AUTH":
        username = cmd_dict["User"]
        password = cmd_dict["Password"]
        valid = authenticator(username, password)
        if valid:
            return json.dumps({"StatusCode": ROOT_SUCCESS_CODE, "Description": "Successfully logged in. Proceed"})
        else:
            return json.dumps(
                {"StatusCode": ROOT_FAILURE_CODE, "Description": "Failure in granting root accessibility"})

    if cmd == "QUIT":
        print(f"[CONNECTION TERMINATED] {addr}")
        return json.dumps({"StatusCode": QUIT_CODE, "Description": "connection terminated!"})

    global data_socket
    if cmd == "LIST":
        directory_files = list_enquirer()
        if directory_files:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            sock.listen()
            port_number = sock.getsockname()[1]
            data_socket = sock
            print("[FULL SERVER]")
            return json.dumps(
                {"StatusCode": SEND_OK_CODE, "Description": "PORT command successful", "DataPort": str(port_number)})
        else:
            print("[EMPTY SERVER]")
            return json.dumps({"StatusCode": EMPTY_DIR_CODE, "Description": "Empty"})

    if cmd == "GET":
        file_name = cmd_dict["FileName"]
        file_names = list_enquirer()

        if file_names and (file_name in file_names):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            sock.listen()
            port_number = sock.getsockname()[1]
            data_socket = sock
            return json.dumps(
                {"StatusCode": SEND_OK_CODE, "Description": "OK to send data", "DataPort": str(port_number)})
        else:
            return json.dumps({"StatusCode": NON_EXISTENT_FILE_CODE, "Description": "File doesn't exist"})

    if cmd == "PUT":
        if root_access:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            sock.listen()
            port_number = sock.getsockname()[1]
            data_socket = sock
            return json.dumps(
                {"StatusCode": SEND_OK_CODE, "Description": "OK to send data", "DataPort": str(port_number)})
        else:
            return json.dumps({"StatusCode": NO_ACCESS_CODE, "Description":
                "The client doesn't have the root access. File transfer aborted."})

    if cmd == "MPUT":
        if root_access:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            sock.listen()
            port_number = sock.getsockname()[1]
            data_socket = sock
            return json.dumps(
                {"StatusCode": SEND_OK_CODE, "Description": "OK to send data", "DataPort": str(port_number)})
        else:
            return json.dumps({"StatusCode": NO_ACCESS_CODE, "Description":
                "The client doesn't have the root access."})

    if cmd == "DELE":
        file_name = cmd_dict["FileName"]
        file_names = list_enquirer()

        if root_access:
            if file_names and (file_name in file_names):
                file_path = get_path() + "/" + file_name
                os.remove(file_path)
                return json.dumps({"StatusCode": DELETE_SUCCESS_CODE, "Description": "Successfully deleted"})
            else:
                return json.dumps({"StatusCode": NON_EXISTENT_FILE_CODE, "Description": "File doesn't exist"})
        else:
            return json.dumps({"StatusCode": NO_ACCESS_CODE, "Description": "The client doesn't have the root access"})

    if cmd == "NONE":
        print("[INVALID COMMAND]")
        return json.dumps({"StatusCode": INVALID_CODE, "Description": "Invalid Command!"})


def authenticator(username, password):
    if username in root_users.keys():
        root_pass = root_users.get(username)
        if root_pass == password:
            print(f"[AUTHENTICATION SUCCESS] welcome, {username}")
            return True
        else:
            print("[INVALID PASSWORD]")
    else:
        print(f"[INVALID USER] {username} doesn't exist")
    return False


def get_path():
    return os.path.dirname(os.path.abspath(__file__))


def list_enquirer():
    path = get_path()
    directory = os.listdir(path)
    if len(directory) == 1:
        return None
    else:
        return directory


def start():
    server.listen()
    print(f"[LISTENING] Server is listening {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


print("[STARTING] server is starting...")
start()
