import socket
import threading
import json
import os
import random
import time
from datetime import datetime, timedelta

PORT = 9001
# SERVER = socket.gethostbyname(socket.gethostname())
SERVER = '0.0.0.0' #za ceo internet
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def rand_test():
    test_values = ['Pozitivan', 'Negativan']

    return random.choice(test_values)

def database_read(file):
    with open(file,'r') as database:
        if os.stat(file).st_size > 0:
            loaded = json.load(database)
            if file == 'users.json':
                user_list = loaded["users"]
                return user_list
            else:
                test_list = loaded["tests"]
                return test_list
        else:
            return []

def database_write(file, data):
    with open(file,'w') as database:
        if file == 'users.json':
            data = {"users":data}
        else:
            data = {"tests":data}

        json.dump(data,database)

def check_if_tested(username, conn):
    tested = False

    test_list = database_read('evaluation_tests.json')
    if test_list !=[]:
        for test in test_list:
            if test['username'] == username:
                tested_time = test['time']
                tested_time = datetime(tested_time[0],tested_time[1],tested_time[2],tested_time[3],tested_time[4]) + timedelta(days=1)
                margin_time = datetime.now()
                if tested_time > margin_time:
                    tested = True
                    break
    else:
        conn.send(json.dumps("NO_DATA").encode(FORMAT))
        return

    if tested:
        print("[STATUS] Korisnik ["+username+"] je pokušao da se testira ali je već testiran")
        conn.send('TESTED'.encode(FORMAT))
        time.sleep(0.1)
        conn.send(str(tested_time-margin_time).encode(FORMAT))   
    else:
        print("[STATUS] Korisnik ["+username+"] je pokrenuo test")
        conn.send('NOT_TESTED'.encode(FORMAT))

def update_pcr(username,message):
    test_list = database_read('evaluation_tests.json')
    for test in test_list:
        if test['username'] == username:
            last_test_index = test_list.index(test)
    test_list[last_test_index]['pcr_test'] = message

    if message == "Pozitivan" or message == "Negativan":
        test_list[last_test_index]['status'] = message

    database_write('evaluation_tests.json',test_list)

def pcr_test(username):
    time.sleep(10)
    update_pcr(username,'poslato')
    time.sleep(10)
    update_pcr(username,'u obradi')
    time.sleep(10)
    status = rand_test()
    update_pcr(username, status)

    users = database_read('users.json')
    for user in users:
        if user['username'] == username:
            user['status'] = status
            break
    database_write('users.json',users)
                
def test_user(data, username, conn):
    count = 0
    for _ , value in data.items():
        if value == "da":
            count +=1
    # Ako treba da se testira   
    if count >=2:
        conn.send("TEST_NEEDED".encode(FORMAT))
        test_type = conn.recv(1).decode(FORMAT)
        # Brzi test
        if test_type == "1":
            test_res = rand_test()
            user_status = test_res
            data['brzi_test'] = test_res
            data['status'] = test_res
            data['pcr_test'] = "/"
            conn.send(test_res.encode(FORMAT))
        # PCR test
        elif test_type == "2":
            user_status = "Ceka se PCR"
            data['brzi_test'] = "/"
            data['status'] = "Ceka se PCR"
            data['pcr_test'] = "Na cekanju"
            thread = threading.Thread(target=pcr_test, args=(username,))
            thread.start()
        # Oba
        else:
            test_res = rand_test()
            thread = threading.Thread(target=pcr_test, args=(username,))
            thread.start()
            user_status = test_res
            data['brzi_test'] = test_res
            data['status'] = test_res
            data['pcr_test'] = "Na čekanju"
            conn.send(test_res.encode(FORMAT))
    # Ako ne treba da se testira
    else:
        data['brzi_test'] = "/"
        data['pcr_test'] = "/"

        user_list = database_read('users.json')
        for user in user_list:
            if user['username'] == username:
                pom = user['status']
                break
        if pom == "Pod nadzorom":
            user_status = 'Negativan'
            data['status'] = 'Negativan'
            conn.send("NEGATIVE".encode(FORMAT))
        else:
            conn.send("NADZOR".encode(FORMAT))
            user_status = 'Pod nadzorom'
            data['status'] = 'Pod nadzorom'

    return {"data":data,"user_status":user_status}

def send_last_login_and_test(conn, username):
    user_list = database_read('users.json')
    for user in user_list:
        if username == user['username']:
            last_login = user['last_login']
            last_test = user['last_test']
            data = {'last_login':last_login, 'last_test':last_test}
            data = json.dumps(data)
            conn.send(data.encode(FORMAT))
            break

def handle_client(conn, addr):
    username = 'unknown'
    print(f"[NEW CONNECTION] {addr} connected.")

    connected = True
    logged = False
    admin = False
    try:        
        while connected:
            status = conn.recv(20).decode(FORMAT)
            message = conn.recv(2048).decode(FORMAT)
            # Korisnik je ulogovan
            if logged:
                # Korisnik je admin
                if admin:
                    if status == 'EXIT':
                            logged = False
                            admin = False
                            print("[ADMIN LOGGED OUT]")
                            print(f"[ACTIVE CONNECTIONS] {threading.activeCount()-2}")
                            break 

                    elif status == 'ADMIN_DATA':
                        pom = [0,0,0]
                        user_list = database_read('users.json')
                        for user in user_list:
                            if user['status'] == "Pod nadzorom":
                                pom[2]+=1
                        test_list = database_read('evaluation_tests.json')

                        data = {}
                        data['count'] = len(test_list)

                        for test in test_list:
                            if test['status'] == "Pozitivan":
                                pom[0]+=1
                            elif test['status'] == "Negativan":
                                pom[1]+=1

                        data['status'] = pom
                        data = json.dumps(data)
                        print("[SEND] Data to admin")
                        conn.send(data.encode(FORMAT))

                    elif status == 'NEW_LIST':
                        changed = False
                        user_list = database_read('users.json')
                        new_positive = []
                        nadzor = []
                        margin_time = datetime.now()
                        for user in user_list:
                            if user['status'] == "Pozitivan" and user['seen'] == "False":
                                new_positive.append(user)
                                changed = True
                                user['seen'] = "True"
                            if user['status'] == "Pod nadzorom":
                                tested_time = user['last_test']
                                tested_time = datetime(tested_time[0],tested_time[1],tested_time[2],tested_time[3],tested_time[4]) + timedelta(days=1)
                                if tested_time < datetime.now():
                                    nadzor.append(user)
                        if changed:
                            database_write('users.json',user_list)
                            
                        return_data = {'nadzor':nadzor, 'new_positive':new_positive}
                        return_data = json.dumps(return_data)
                        conn.send(return_data.encode(FORMAT))

                    elif status == 'ALL_USERS':
                        all_users = database_read('users.json')
                        all_users = json.dumps(all_users)
                        conn.send(all_users.encode(FORMAT))

                    elif status == 'ALL_POSITIVE':
                        all_users = database_read('users.json')
                        return_data = []
                        for user in all_users:
                            if user['status'] == "Pozitivan":
                                return_data.append(user)
                        return_data = json.dumps(return_data)
                        conn.send(return_data.encode(FORMAT))

                    elif status == 'ALL_NEGATIVE':
                        all_users = database_read('users.json')
                        return_data = []
                        for user in all_users:
                            if user['status'] == "Negativan":
                                return_data.append(user)
                        return_data = json.dumps(return_data)
                        conn.send(return_data.encode(FORMAT))

                    elif status == 'ALL_NADZOR':
                        all_users = database_read('users.json')
                        return_data = []
                        for user in all_users:
                            if user['status'] == "Pod nadzorom":
                                return_data.append(user)
                        return_data = json.dumps(return_data)
                        conn.send(return_data.encode(FORMAT))

                # Korisnik je obican
                else:
                    if status == 'EXIT':
                        print("[DISCONNECT] Korisnik ["+username+"] se odjavio")
                        print(f"[ACTIVE CONNECTIONS] {threading.activeCount()-2}")
                        break  

                    if status == 'CHECK':
                        check_if_tested(username, conn) 

                    if status == 'TEST':
                        user_status = ''

                        data = json.loads(message)

                        pom = test_user(data, username, conn)
                        data = pom['data']
                        user_status = pom['user_status']
                        data['time'] = time.localtime()

                        test_list = database_read('evaluation_tests.json')
                        test_list.append(data)
                        database_write('evaluation_tests.json', test_list)

                        user_list = database_read('users.json')
                        for user in user_list:
                            if user['username'] == username:
                                user['status'] = user_status
                                user['last_test'] = time.localtime()
                                user['seen'] = "False"
                                break
                        
                        database_write('users.json', user_list)
                
                    if status == 'USER_DATA':
                        return_data = []
                        time.sleep(0.1)
                        test_list = database_read('evaluation_tests.json')
                        if test_list == []:
                            conn.send(json.dumps('NO_DATA').encode(FORMAT))
                        else:
                            for test in test_list:
                                if username == test['username']:
                                    return_data.append(test)   
                            return_data = {"data":return_data}
                            return_data = json.dumps(return_data)
                            conn.send(return_data.encode(FORMAT))                                        
            
            # Korisnik nije ulogovan
            else:
                if status == 'REGISTER':
                    user_list = database_read('users.json')
                    data = json.loads(message)
                    used_username = False

                    if user_list !=[]:
                        for user in user_list:
                            if user['username'] == data['username']:
                                used_username = True
                                break
                    if data['username'] == 'admin':
                        used_username = True

                    if used_username==False:
                        data['last_test'] = ''
                        data['last_login'] = ''
                        user_list.append(data)
                        database_write('users.json', user_list)
                        conn.send("OK".encode(FORMAT))
                        print("[REGISTER] Korisnik ["+data['username']+"] se uspesno registrovao")
                    else:
                        conn.send("NO".encode(FORMAT))

                elif status == 'LOGIN':
                    login_time = time.localtime()
                    user_list = database_read('users.json')
                    data = json.loads(message)

                    if user_list == []:
                        conn.send("NO".encode(FORMAT))
                    else:
                        if data['username'] == "admin" and data['password'] == "admin":
                            username = 'ADMIN'
                            conn.send("AD".encode(FORMAT))
                            logged = True
                            admin = True
                            print("[ADMIN LOGGED IN]")
                        else:
                            found = False
                            for user in user_list:
                                if user['username'] == data['username'] and user['password'] == data['password']:
                                    username = str(data['username'])
                                    print('[CONNECT] Korisnik ['+username+'] se uspesno ulogovao')
                                    logged = True
                                    found = True
                                    conn.send("OK".encode(FORMAT))
                                    send_last_login_and_test(conn,username)
                                    user['last_login'] = login_time
                                    database_write('users.json',user_list)
                                    break
                            if found == False:
                                conn.send("NO".encode(FORMAT))     
        
    except ConnectionResetError:
        print("[DISCONNECT] Klijent ["+username+"] je prekinuo konekciju")
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount()-2}")
    except Exception as e:
        print("Došlo je do greške")
        print(e)
    conn.close()

def start():
    server.listen()
    print(f"[LISTENING] Server sluša na {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount()-1}")

print("[STARTING] Server se pokreće...")
start()