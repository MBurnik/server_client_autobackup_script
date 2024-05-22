import socket
import os
import csv
import bcrypt


#-----------------------------------------------------------------------------------------------------------------------------------------
# Logowanie

def login(attempt):
    name, temp = receive_msg()                                                      # Otrzymanie logina oraz hasła
    password, temp = receive_msg()
    if (name in database) and (bcrypt.checkpw(password.encode("utf-8"), (database[name]).encode())):
        send_msg('@@OK_@@')                                                         # Sprawdzenie istnienia loginu oraz porównanie zahashowanego hasła z otrzymanym
        if not os.path.isdir(name):                                                 # Utworzenie katalogu użytkownika
            os.mkdir(name)
        os.chdir(name)
        return name                                                                 # Zwrócenie loginu
    else:
        attempt -= 1
        if attempt == 0:                                                            # Wysłanie użytkownikowi kodu do rozłączenia
            send_msg('@@CLS@@')
            return None
        send_msg(f'@@BAD@@Pozostala ilosc prob: {attempt}')                         # Wysyłanie użytkownikowi komunikatu zwrotnego
        return login(attempt)
    

#-----------------------------------------------------------------------------------------------------------------------------------------
# Komunikacja

def receive_msg():
    codes = ['NAM', 'DAT', 'FMT', 'DIR', 'SNC', 'PTH', 'CLS']
    message = ''
    
    data = c.recv(buffer_size).decode()                                             # Otrzymanie długości wiadomości w formie zaszyfrowanej
    data = decrypt(data)                                                            # Deszyfrowanie długości wiadomości

    message_size = int(data)                                                        # Przeładowanie zmiennej długością wiadomości
    temp = encrypt('A')
    c.send(temp.encode())                                                           # Wymuszenie opóźnienia

    byte_message = []

    while message_size > buffer_size:
        data = c.recv(buffer_size)                                                  # Otrzymanie części wiadomości w binarce w formie zaszyfrowanej
        byte_message.append(data)

        message_size -= buffer_size

    if message_size <= buffer_size:
        data = c.recv(message_size)                                                 # Otrzymanie ostatniej części wiadomości w binarce w formie zaszyfrowanej
        byte_message.append(data)

    message = b''.join(byte_message)                                                # Scalanie wiadomości w binarce w formie zaszyfrowanej
    message = message.decode()                                                      # Dekodowanie zaszyfrowanej wiadomości

    message = decrypt(message)                                                      # Deszyfrowanie wiadomości
    message_copy = message

    temp_data_list = message.split('@@')                                            # Rozdzielenie wiadomości oraz czyszczenie listy z elementów pustych
    for i in temp_data_list:
        if i == '':
            temp_data_list.remove(i)

    content_of_file = b''
    code = temp_data_list[0]
    if code == 'DAT':
        filesize = int(temp_data_list[1])                                           
        byte_data = []
        while filesize > 0:                                                         # Otrzymanie zawartości pliku jeżeli jest
            if filesize > buffer_size:                                              
                data = c.recv(buffer_size)
                byte_data.append(data)
                filesize -= buffer_size
            else:
                data = c.recv(filesize)
                byte_data.append(data)
                filesize -= buffer_size

        content_of_file = b''.join(byte_data)                                       # Scalanie zawartości pliku
        content_of_file = decrypt_XOR(content_of_file)                              # Deszyfrowanie zawartości pliku

    elif code == 'DIR':
        directory = message_copy[7:]
        temp_data_list = []
        temp_data_list.append(code)
        temp_data_list.append(directory)

    elif code == 'NAM':
        filename = message_copy[7:]
        temp_data_list = []
        temp_data_list.append(code)
        temp_data_list.append(filename)

    elif code == 'SNC':
        mod_date = temp_data_list[-1]
        lenght_mod_date = len(mod_date) +2
        filename = message_copy[7:-lenght_mod_date]
        temp_data_list = []
        temp_data_list.append(code)
        temp_data_list.append(filename)
        temp_data_list.append(mod_date)

    elif not (code in codes):
        temp_data_list = message_copy

    return temp_data_list, content_of_file                                          # Zwracanie gotowej wiadomości w formie listy/stringu, zawartości pliku w formie binarki


def send_msg(message):
    message = str(message)

    data_lenght = len(bytes(message, encoding="utf-8"))                             # Określenie długości wiadomości w binarce, ponieważ się różni od dlugości w utf-8

    data = encrypt(message)                                                         # Zaszyfrowanie wiadomości
    data_lenght = encrypt(data_lenght)                                              # Zaszyfrowanie długości wiadomości

    c.send(data_lenght.encode())                                                    # Wysłanie zaszyfrowanej długości wiadomości
    c.recv(buffer_size)                                                             # Wymuszenie opóźnienia
    c.sendall(data.encode())                                                        # Wysłanie zaszyfrowanej wiadomości


#-----------------------------------------------------------------------------------------------------------------------------------------
# Szyfrowanie, deszyfrowanie

def encrypt(message):
    data = ''
    message = str(message)
    for i in range(len(message)):                                                   # Algorytm szyfrowania wiadomości zaszyfrowanych w jawnym tekście
        data += chr(ord(message[i]) + 3)
    return data


def decrypt(data):
    message = ''
    for i in range(len(data)):                                                      # Algorytm deszyfrowania wiadomości zaszyfrowanych w jawnym tekście
        message += chr(ord(data[i]) - 3)
    return message


def decrypt_XOR(data):
    key = 247                                                                       # Algorytm deszyfrowania wiadomości zaszyfrowanych w binarce
    data = bytearray([byte ^ key for byte in data])
    return data


#-----------------------------------------------------------------------------------------------------------------------------------------
# Synchronizacja

def autosync(user):
    synced_files = 0

    if os.path.isfile("paths.txt"):                                                 # Otwarcie pliku paths.txt jeżeli istnieje
        f = open("paths.txt", "r")
        lines = []
        for line in f:                                                              # Zczytanie ścieżek z pliku paths.txt
            lines.append(line[:-1])

        for path in lines:                                                          # Dla każdej ścieżki w pliku
            send_msg(path)                                                          # Wysyła ścieżkę
            synced_files += copy_to_storage(user)                                   # Wykonywanie synchronizacji, otrzymanie licznika zsynchronizowanych plików oraz katalogów
                
    send_msg(f'@@EOS@@Liczba zsynchronizowanych plikow: {synced_files}')            # Wysłanie kodu zakończenia synchronizacji, statusu


#-----------------------------------------------------------------------------------------------------------------------------------------
# Kopia struktury danych

def copy_to_storage(user):
    check_CLS = 0
    new_files = 0
    while True:
        if check_CLS == 1:
            break

        data_list, content_of_file = receive_msg()                                  # Otrzymanie wiadomości w formie listy 

        i = 0
        while i < len(data_list):                                                   # Sprawdzanie kodów oraz podejmowanie decyzji
            if data_list[i] == 'PTH':                                               # Otrzymanie kodu o ścieżce
                os.chdir(f'{server_storage}/{user}')
                check_is_path = 0
                if not os.path.isfile("paths.txt"):                                 # Stworzenie pliku paths.txt jeżeli nie istnieje
                    f = open("paths.txt", "w")
                    f.close()
                with open("paths.txt", "r+") as f:                                  # Sprawdzanie czy plik paths.txt już zawiera scieżkę
                    for line in f:
                        if line[:-1] == data_list[i+1]:
                            check_is_path = 1
                            break
                    if check_is_path == 0:                                          # Dodanie ścieżki do pliku paths.txt jeżeli nie występuje
                        f.seek(0, 2)
                        f.write(f'{data_list[i+1]}\n')

            elif data_list[i] == 'DIR':                                             # Otrzymanie kodu o katalogu
                os.chdir(f'{server_storage}/{user}')

                path = data_list[i+1]
                directory = os.path.basename(os.path.normpath(path))

                os.chdir(f'{server_storage}/{user}/{os.path.dirname(path)}')

                if not os.path.isdir(directory):                                    # Stworzenie katalogu jeżeli nie istnieje
                    os.mkdir(directory)
                    new_files += 1

                os.chdir(directory)                                                 # Zmiana aktywnego katalogu na nowo utworzony
            
            elif data_list[i] == 'SNC':                                             # Otrzymanie kodu o synchronizacji
                if os.path.isfile(data_list[i+1]):
                    modification_time = os.path.getmtime(data_list[i+1])
                    if modification_time == float(data_list[i+2]):                  # Porównianie czasu modyfikacji pliku na serwerze z otrzymanym
                        send_msg('@@SKP@@')                                         # Wysłanie kodu, że plik jest aktualny
                    else:
                        send_msg('@@TRQ@@')                                         # Wysłanie kodu prośby o synchronizację

                else:
                    send_msg('@@TRQ@@')                                             

            elif data_list[i] == 'NAM':                                             # Otrzymanie kodu o nazwie pliku
                filename = data_list[i+1]
                f = open(filename, "wb")                                            # Stworzenie pliku o otrzymanej nazwie

            elif data_list[i] == 'DAT':                                             # Otrzymanie kodu o zawartości otrzymanego pliku
                f.write(content_of_file)
                f.close()                                                           # Zamknięcie pliku

            elif data_list[i] == 'FMT':                                             # Otrzymanie kodu o czasie modyfikacji pliku
                os.utime(filename, (float(data_list[i+1]), float(data_list[i+2])))  # Zmiana czasu stworzenia oraz modyfikacji pliku na odebraną
                new_files += 1                                                      # Zwiększenie licznika zsynchronizowanych plików oraz katalogów

            elif data_list[i] == 'CLS':                                             # Otrzymanie kodu o zakończeniu pracy z klientem
                check_CLS = 1
                break
        
            i += 1

    return new_files


#-----------------------------------------------------------------------------------------------------------------------------------------
# Kody obsługi połączenia

# @@OK_@@ - zalogowano
# @@BAD@@ - złe dane przy logowaniu
# @@SKP@@ - skip; przejdź do kolejnego pliku podczas synchronizacji
# @@TRQ@@ - to request; zażądaj pliku podczas synchronizacji
# @@SNC@@ - synchronizuj
# @@EOS@@ - end of sync
# @@DIR@@ - directory
# @@NAM@@ - filename
# @@DAT@@ - data
# @@FMT@@ - file modification time
# @@CLS@@ - zakonczenie kopiowania/synchronizacji


#-----------------------------------------------------------------------------------------------------------------------------------------
# Główny skrypt

server_ip = '127.0.0.1'                                                             # Konfiguracja połączenia
server_port = 40444
buffer_size = 1024
max_buffer_size = 65536

s = socket.socket()
s.bind((server_ip, server_port))
s.listen(5)

server_storage = f'{os.getcwd()}/SERVER_STORAGE'
os.chdir(server_storage)

database = dict()                                                                   # Wczytanie zawartości bazy danych zawierającej loginy i hasła
f = open('database.csv', 'r')
reader = csv.reader(f)
database = {rows[0]:rows[1] for rows in reader}
f.close()

attempt = 5

while True:                                                                         # Nieskończona pętla, umożliwia wykonywanie powtórnego połączenia użytkownikowi
    os.chdir(server_storage)
    while True:
        print('Oczekiwanie na polaczenie...')
        c, address = s.accept()
        print(f'Otrzymano polaczenie z adresu: {address}')
        
        user = login(attempt)
        if user:
            break
        else:
            c.close()

    autosync(user)

    temp = copy_to_storage(user)

    print('Zamkniecie polaczenia\n')
    c.close()