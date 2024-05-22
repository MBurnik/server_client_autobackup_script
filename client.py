import socket
import os
import maskpass


#-----------------------------------------------------------------------------------------------------------------------------------------
# Łączenie

def connect_to_server(attempt):
    ip = input('Podaj adres IP: ')                                                 
    if ip == server_ip:                                                             # Porównanie podanego IP z IP serwera
        s.connect((server_ip, server_port))                                         # Połączenie z serwerem
    else:
        attempt -= 1                                                                # Odliczanie prób połączenia
        if attempt <= 0:                                                            # Zamknięcie skryptu po osiągnięciu limitu prób
            print('Osiagnieto limit prob!\nZamykanie skryptu')
            quit()
        print(f'Niepoprawny adres ip!\nPozostala ilosc prob: {attempt}')
        connect_to_server(attempt)                                                  # Rekurencja próby łączenia się z serwerem


#-----------------------------------------------------------------------------------------------------------------------------------------
# Logowanie

def login():
    while True:
        name = input('Login: ')
        password = maskpass.askpass(mask="", prompt="Haslo: ")
        if not ((name or password) == ''):
            break
    send_msg(f'{name}')
    send_msg(f'{password}')                                                         # Wysłanie loginu oraz hasła
    response = receive_msg()                                                        # Otrzymanie kodu zwrotnego
    if response[0] == 'OK_':                                                        # Jeżeli dane były poprawne to zalogowno do serwera
        print('Zalogowano do serwera\n')
    elif response[0] == 'BAD':                                                      # Jeżeli nie to wymuszenie ponownego logowania
        print(f'Niepoprawne dane! {response[1]}\n')
        login()
    elif response[0] == 'CLS':
        print('Zamykanie skryptu')
        s.close()
        quit()


#-----------------------------------------------------------------------------------------------------------------------------------------
# Komunikacja

def receive_msg():
    message = ''
    
    data = s.recv(buffer_size).decode()                                             # Otrzymanie długości wiadomości w formie zaszyfrowanej
    data = decrypt(data)                                                            # Deszyfrowanie długości wiadomości

    message_size = int(data)                                                        # Przeładowanie zmiennej długością wiadomości
    temp = encrypt('A')
    s.send(temp.encode())                                                           # Wymuszenie opóźnienia

    byte_message = []

    while message_size > buffer_size:
        data = s.recv(buffer_size)                                                  # Otrzymanie części wiadomości w binarce w formie zaszyfrowanej
        byte_message.append(data)

        message_size -= buffer_size

    if message_size <= buffer_size:
        data = s.recv(message_size)                                                 # Otrzymanie ostatniej części wiadomości w binarce w formie zaszyfrowanej
        byte_message.append(data)

    message = b''.join(byte_message)                                                # Scalanie wiadomości w binarce w formie zaszyfrowanej
    message = message.decode()                                                      # Dekodowanie zaszyfrowanej wiadomości

    message = decrypt(message)                                                      # Deszyfrowanie wiadomości

    temp_data_list = message.split('@@')                                            # Rozdzielenie wiadomości oraz czyszczenie listy z elementów pustych
    for i in temp_data_list:
        if i == '':
            temp_data_list.remove(i)

    return temp_data_list                                                           # Zwracanie gotowej wiadomości w formie listy


def send_data(data):
    data = encrypt_XOR(data)                                                        # Zaszyfrowanie zawartości pliku
    s.sendall(data)                                                                 # Wysłanie zaszyfrowanej zawartości pliku


def send_msg(message):
    data_lenght = len(bytes(message, encoding="utf-8"))                             # Określenie długości wiadomości w binarce, ponieważ się różni od dlugości w utf-8

    data = encrypt(message)                                                         # Zaszyfrowanie wiadomości
    data_lenght = encrypt(data_lenght)                                              # Zaszyfrowanie długości wiadomości

    s.send(data_lenght.encode())                                                    # Wysłanie zaszyfrowanej długości wiadomości
    s.recv(buffer_size)                                                             # Wymuszenie opóźnienia
    s.sendall(data.encode())                                                        # Wysłanie zaszyfrowanej wiadomości


#-----------------------------------------------------------------------------------------------------------------------------------------
# Szyfrowanie, deszyfrowanie

def encrypt(message):
    data = ''
    message = str(message)
    for i in range(len(message)):                                                   # Algorytm szyfrowania wiadomości zaszyfrowanych w jawnym tekście
        data += chr(ord(message[i]) + 3)
    return data


def encrypt_XOR(message):
    key = 247                                                                       # Algorytm szyfrowania wiadomości zaszyfrowanych w binarce
    message = bytearray([byte ^ key for byte in message])
    return message


def decrypt(data):
    message = ''
    for i in range(len(data)):                                                      # Algorytm deszyfrowania wiadomości zaszyfrowanych w jawnym tekście
        message += chr(ord(data[i]) - 3)
    return message


#-----------------------------------------------------------------------------------------------------------------------------------------
# Sortowanie

def sort(content):
    files = []
    directories = []
    for file in content:                                                            # Posortowanie zawartości katalogu na listę plików oraz na listę katalogów
        if os.path.isfile(file):
            files.append(file)
        elif os.path.isdir(file):
            directories.append(file)
    return files, directories


#-----------------------------------------------------------------------------------------------------------------------------------------
# Operacje na pliku

def send_file(filename):
    send_msg(f'@@NAM@@{filename}')                                                  # Wysłanie kodu oraz nazwy pliku
    with open(filename, "rb") as f:
        send_msg(f'@@DAT@@{os.path.getsize(filename)}')                             # Wysłanie kodu oraz wielkość pliku
        send_data(f.read())
    modification_time = os.path.getmtime(filename)
    creation_time = os.path.getctime(filename)
    send_msg(f'@@FMT@@{creation_time}@@{modification_time}')                        # Wysłanie kodu, czasu stworzenia oraz modyfikacji pliku


#-----------------------------------------------------------------------------------------------------------------------------------------
# Synchronizacja

def autosync():
    print('Autosynchronizacja...')
    while True:
        data_list = receive_msg()                                                   # Otrzymanie ścieżki do synchronizacji lub kodu zakończenia synchronizacji

        if data_list[0] == 'EOS':                                                   # Otrzymanie kodu o zakończeniu synchronizacji
            print(f'Autosynchronizacja zakonczona\n{data_list[1]}\n')
            break
        else:
            if os.path.isdir(data_list[0]):                                         # Jeżeli istnieje ścieżka
                path = data_list[0]
                os.chdir(os.path.dirname(path))
                path = os.path.basename(os.path.normpath(path))
                copy_to_server(path, 'sync')                                        # Zacznij synchronizację
                send_msg('@@CLS@@')                                                 # Wyślij kod o zakończeniu synchronizacji ścieżki


#-----------------------------------------------------------------------------------------------------------------------------------------
# Kopia struktury danych

def copy_to_server(path, task):
    directory = os.path.basename(os.path.normpath(path))
    os.chdir(directory)                                                             # Zmiana aktywnej ścieżki
    content = os.listdir('./')                                                      # Wyciągnięcie zawartości katalogu

    send_msg(f'@@DIR@@{path}')                                                      # Wysłanie kodu oraz ścieżki

    if content:                                                                     # Jeżeli istnieje zawartość katalogu
        files, directories = sort(content)                                          # Posortowanie zawartości katalogu na listę plików oraz na listę katalogów
        
        for filename in files:
            if task == 'sync':
                send_msg(f'@@SNC@@{filename}@@{os.path.getmtime(filename)}')        # Wysłanie kodu, nazwy pliku oraz czasu modyfikacji
                data = receive_msg()                                                # Otrzymanie kodu zwrotnego
                if data[0] == 'TRQ':                                                # Przejdź do kolejnego pliku
                    send_file(filename)                                             # Wysyłanie pliku
            else:
                send_file(filename)

        i = 0
        while i < len(directories):                                                 # Rekursywne przechodzenie do katalogów oraz wysyłanie plików
            directory = f'{path}/{directories[i]}'
            if os.path.islink(directories[i]):
                send_msg(f'@@DIR@@{directory}')                                     # Wysłanie kodu oraz ścieżki jeżeli jest linkiem
            else:
                copy_to_server(directory, task)
                os.chdir('../')
            i += 1


def manual_copy():
    while True:
        os.chdir(script_location)
        option = input('Wybierz opcje (np. 1):\n1.Kopiuj pliki\n2.Zakoncz\n')       # Wybranie opcji wyboru
        if option == '1':                                                           # Porównanie ze str po zabezpieczenie przed wpisaniem innego typu danych niż int
            path = os.path.abspath(input('\nPodaj sciezke do skopiowania: '))       # Określenie ścieżki do skopiowania
            print(path)
            while not os.path.isdir(path):
                path = os.path.abspath(input('Podaj poprawna sciezke do skopiowania: '))
                print(path)
            
            print('\nKopiowanie...')
            send_msg(f'@@PTH@@{path}')                                              # Wysłanie kodu oraz główną ścieżkę
            os.chdir(os.path.dirname(path))
            path = os.path.basename(os.path.normpath(path))
            copy_to_server(path, 'copy')                                            # Wykonywanie kopii plików oraz katalogów na serwer
            print('Kopiowanie zakonczone\n')

        elif option == '2':                                                         # Zakończenie pracy z serwerem
            break
            
    send_msg('@@CLS@@')                                                             # Wysłanie kodu zakończenia pracy z serwerem


#-----------------------------------------------------------------------------------------------------------------------------------------
# Główny skrypt

server_ip = '127.0.0.1'                                                             # Konfiguracja połączenia
server_port = 40444
buffer_size = 1024

s = socket.socket()

script_location = os.getcwd()
attempt = 5

connect_to_server(attempt)    
login()
autosync()
manual_copy()

s.close()