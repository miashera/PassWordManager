from cryptography.fernet import Fernet

# Generate a random encryption key
def generate_key():
    key = Fernet.generate_key()
    with open("key.key", "wb") as key_file:
        key_file.write(key)

# Load the encryption key from a file
def load_key():
    return open("key.key", "rb").read()

# Encrypt a password
def encrypt_password(password, key):
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(password.encode())
    return encrypted_password

# Decrypt an encrypted password
def decrypt_password(encrypted_password, key):
    cipher_suite = Fernet(key)
    decrypted_password = cipher_suite.decrypt(encrypted_password)
    return decrypted_password.decode()

# Generate and save a key
generate_key()

# Load the key
key = load_key()

# Get a password from the user
password = input("Enter a password: ")

# Encrypt and save the password
encrypted_password = encrypt_password(password, key)
with open("encrypted_password.txt", "wb") as password_file:
    password_file.write(encrypted_password)

# Decrypt and print the password
with open("encrypted_password.txt", "rb") as password_file:
    encrypted_password = password_file.read()
    decrypted_password = decrypt_password(encrypted_password, key)
    print("Decrypted password:", decrypted_password)