import socket
import json
import getpass
import time
import os

HEADER = 64
PORT = 9001
FORMAT = 'utf-8'
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

registration = {
    'username': '',
    'password': '',
    'name': '',
    'surname': '',
    'gender': '',
    'email':'',
    'status':''
}

log = {
    'username': '',
    'password': ''
}

test = {}

clear = lambda: os.system('cls')

def send(msg, status='non'):
    message = json.dumps(msg)
    client.send(status.encode(FORMAT))
    client.send(message.encode(FORMAT))
    if status == 'EXIT':
        client.close()
        return

    return client.recv(2048).decode(FORMAT)

def format_time(time):
    return str(time[2])+'.'+str(time[1])+'.'+str(time[0])+'. '+str(time[3])+':'+str(time[4])

def login():
    log['username'] = input("Unesite username: ")
    log['password'] = getpass.getpass(prompt="Unesite šifru: ")
    status = send(log, 'LOGIN')
    if status == 'OK':
        logs = client.recv(2048).decode(FORMAT)
        logs = json.loads(logs)
        print("Uspesno ste se ulogovali")
        if logs['last_login'] != '':
            print("Vreme poslednjeg logina: "+format_time(logs['last_login']))
        if logs['last_test'] != '':
            print("Vreme poslednjeg testa: "+format_time(logs['last_test']))

        return True
    if status == "AD":
        print("Dobrodosao admine")
        global admin
        admin = True
        return True
    print("Pokusajte ponovo")
    return False

def register():
    # Sredi validaciju
    registration['username'] = input("Unesite username: ")
    registration['password'] = getpass.getpass(prompt="Unesite šifru: ")
    registration['name'] = input("Unesite ime: ")
    registration['surname'] = input("Unesite prezime: ")
    registration['gender'] = input("Unesite pol: ")
    registration['email'] = input("Unesite e-mail: ")
    registration['status'] = 'nepoznat'

    response = send(registration, 'REGISTER')

    if response == "OK":
        print("Uspesno ste se registrovali "+ registration['name'])
        print()
        return True
    elif response == 'NO':
        print("Korisničko ime ["+registration['username']+'] je zauzeto')
        print()
        return register()

    print("Doslo je do greske")
    return False

def user_test_data():
    data = send('', 'USER_DATA')
    data = json.loads(data)
    if data == 'NO_DATA':
        print("Još uvek niste uradili ni jedan test")
        return
    if len(data['data']):
        print("Podaci za korisnika ["+data['data'][0]['username']+']')
        print("Putovanja | Kontakt sa zarazenim | Temperatura | Kasalj | Slabost | Gubitak mirisa | Gubitak ukusa | Brzi test | PCR test   | Status       | Vreme")
        print("----------------------------------------------------------------------------------------------------------------------------------------------------------")
        for element in data['data']:
            print("{:9} | {:20} | {:11} | {:6} | {:7} | {:14} | {:13} | {:9} | {:10} | {:12} | {:17}".format(element['putovanja'], element['kontakt_sa_zarazenim'], element['temperatura'], element['kasalj'], element['slabost'], element['gubitak_mirisa'], element['gubitak_ukusa'], element['brzi_test'], element['pcr_test'], element['status'], format_time(element['time'])))
    else:
        print("Još uvek niste uradili ni jedan test")

def covid_test():
    response = send('', 'CHECK')

    if response == 'TESTED':
        print("Rok za sledeci test nakon uradjenog je 24h")
        print("Vreme do sledeceg testa je: "+client.recv(200).decode(FORMAT)[:8])
        return

    test['username'] = log['username']
    print("Sledeći test će proceniti da li je potrebno da se testirate. Odgovarajte sa [da/ne] ")
    test['putovanja'] = input('Da li ste putovali van Srbije u okviru 14 dana pre početka simptoma? ')
    test['kontakt_sa_zarazenim'] = input('Da li ste bili u kontaku sa zaraženim osobama? ')
    print('Šta imate od simptoma:')
    test['temperatura'] = input('Povišena temperatura: ')
    test['kasalj'] = input('Kašalj: ')
    test['slabost'] = input('Opšta slabost: ')
    test['gubitak_mirisa'] = input('Gubitak čula mirisa: ')
    test['gubitak_ukusa'] = input('Gubitak/promena čula ukusa: ')

    status = send(test, 'TEST')

    if status == 'TEST_NEEDED':
        print("Dva ili vise odgovora su bila potvrdna, potrebno je da se testirate")
        print()
        while True:
            print("Unesite 1 za brzi test, 2 za PCR test i 3 za oba testa")
            result = input()
            print()
            if result == "1" or result == "2" or result == "3":
                break
        client.send(result.encode(FORMAT))
        if result == "1" or result == "3":
            test_status = client.recv(20).decode(FORMAT)
            print()
            time.sleep(1)
            if test_status == "Pozitivan":
                print("Vaš test je pozitivan")
            else:
                print("Vaš test je negativan")
            if result == "3":
                print("Vaš PCR test je na čekanju. Stanje možete proveriti u pregledu testova")
    elif status == 'NEGATIVE':
        print("Izaši ste iz nadzora. Vaš status je sada [negativan]")
    elif status == 'NADZOR':
        print("Bicete pod nadzorom, potrebno je da za 24h uradite jos jedan test, u koliko je negativan dobicete status [negativan]")      

def startMenu():
    while True:
        menu = False
        print("1. Log In")
        print("2. Register")
        dec = input("Vaš izbor: ")
        if dec=='1':
            menu = login()
            logged = menu
        elif dec=='2':
            if register():
                print('Ulogujte se sa unetim podacima')
                menu = login()
        if menu:
            break

    menu = False

def userMenu():
    while True:
        print("Testirajte se ili pogledajte vase testove")
        print("1. Test samoprocene")
        print("2. Pregled testova")
        print("3. Izlaz")
        dec = input("Vaš izbor: ")
        print()
        if dec=='1':
            covid_test()
        elif dec=='2':
            user_test_data()
        elif dec=='3':
            break

def get_admin_data():
    data = send('data', 'ADMIN_DATA')
    data = json.loads(data)
    print("Broj testova: "+str(data['count'])+" Broj pozitivnih testova: "+str(data['status'][0])+" Broj negativnih testova: "+str(data['status'][1])+" Broj korisnika pod nadzorom: "+str(data['status'][2]))

def admin_menu():
    while True:
        print("1. Pregled statistike")
        print("2. Pregled svih korisnika")
        print("3. Pregled svih pozitivnih korisnika")
        print("4. Pregled svih negativnih korisnika")
        print("5. Pregled svih korisnika pod nadzorom")
        print("6. Izlaz")
        dec = input("Vaš izbor: ")
        print()
        if dec=='1':
            get_admin_data()
        elif dec=='2':
            admin_all_users()
        elif dec=='3':
            admin_positive()
        elif dec=='4':
            admin_negative()
        elif dec=='5':
            admin_nadzor()
        elif dec=='6':
            break

def admin_new_list():
    data = send('','NEW_LIST')
    data = json.loads(data)
    new_positive = data['new_positive']
    nadzor = data['nadzor']
    if new_positive:
        print("Novi pozitivni korisnici")
        for user in new_positive:
            print("Ime: "+user['name']+" Prezime: "+user['surname']+" Email: "+user['email'])
    else:
        print("Nema novih pozitivnih korisnika")

    print()

    if nadzor:
        print("Korisnici koji nose status [Pod nadzorom] i treba da urade dodatan test jer je prošlo 24h od poslednjeg testa:")
        for user in nadzor:
            print("Ime: "+user['name']+" Prezime: "+user['surname']+" Email: "+user['email'])
    else:
        print("Nema korisnika pod nadzorom kojima je došao rok za test")

def admin_all_users():
    all_users = send('','ALL_USERS')
    all_users = json.loads(all_users)
    print("Lista svih korisnika: ")
    print(" Ime        |  Prezime     | Email                     | Status")
    print("----------------------------------------------------------------")
    for user in all_users:
        print(" {:10} | {:12} | {:25} | {:11} ".format(user['name'],user['surname'],user['email'],user['status']))

def admin_positive():
    all_users = send('','ALL_POSITIVE')
    all_users = json.loads(all_users)
    print("Lista svih pozitivnih korisnika: ")
    print(" Ime        |  Prezime     | Email                     ")
    print("--------------------------------------------------")
    for user in all_users:
        print(" {:10} | {:12} | {:25}".format(user['name'],user['surname'],user['email']))

def admin_negative():
    all_users = send('','ALL_NEGATIVE')
    all_users = json.loads(all_users)
    print("Lista svih negativnih korisnika: ")
    print(" Ime        |  Prezime     | Email                     ")
    print("--------------------------------------------------")
    for user in all_users:
        print(" {:10} | {:12} | {:25}".format(user['name'],user['surname'],user['email']))

def admin_nadzor():
    all_users = send('','ALL_NADZOR')
    all_users = json.loads(all_users)
    print("Lista svih korisnika pod nadzorom: ")
    print(" Ime        |  Prezime     | Email                     ")
    print("--------------------------------------------------")
    for user in all_users:
        print(" {:10} | {:12} | {:25}".format(user['name'],user['surname'],user['email']))

logged = False
admin = False

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.settimeout(10)

try:
    client.connect(ADDR)
    print("Dobrodosli! Ulogujte se ukoliko imate nalog, u suprotnom se registrujte. Unesite broj ispred opcije")
    # Login i register meni
    startMenu()
    # Meni za admina i obicnog uzera
    if admin:
        time.sleep(0.1)
        admin_new_list()
        time.sleep(0.1)
        admin_menu()
    else:
        userMenu()
    print('Dovidjenja')
    time.sleep(1)
    send('', 'EXIT')
except socket.timeout:
    print("Server nije odgovorio na vreme, pokušajte ponovo")
    time.sleep(2)
except ConnectionResetError:  #server ne radi nakon konekcije
    print("Server je pao, pokušajte kasnije")
    time.sleep(2)
except ConnectionRefusedError: #server ne radi, ne moze da se konektuje
    print("Server je neaktivan, pokušajte kasnije")
    time.sleep(2)
# except Exception:
#     print("Greška")