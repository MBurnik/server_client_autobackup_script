import bcrypt
import csv
import os


name = input('Wprowadz login: ')
password = input('Wprowadz haslo: ')
byte_password = password.encode("utf-8")

salt = bcrypt.gensalt()

hashed_password = str(bcrypt.hashpw(byte_password, salt))[2:-1]
print(hashed_password)

os.chdir(f'{os.getcwd()}/SERVER_STORAGE')

database = dict()                                                                   # Wczytanie zawartości bazy danych zawierającej loginy i hasła
f = open('database.csv', 'r')
reader = csv.reader(f)
database = {rows[0]:rows[1] for rows in reader}
f.close()

database[name] = hashed_password
print(database)

f = open('database.csv', "a")
writer = csv.writer(f)
writer.writerow([name, hashed_password])
f.close()