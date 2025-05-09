import random
import math

def is_prime(n, k=5):
    if n < 2:
        return False
    
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_prime(bit_length):
    while True:
        p = random.getrandbits(bit_length) | (1 << (bit_length - 1)) | 1
        if is_prime(p):
            return p

def egcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = egcd(b, a % b)
    x = y1
    y = x1 - (a // b) * y1
    return g, x, y

def modinv(a, m):
    g, x, _ = egcd(a, m)
    if g != 1:
        raise Exception('Modular inverse does not exist')
    return x % m

def generate_keys(bit_length=1024):
    p = generate_prime(bit_length // 2)
    q = generate_prime(bit_length // 2)
    while q == p:
        q = generate_prime(bit_length // 2)
    
    n = p * q
    phi = (p - 1) * (q - 1)
    
    e = 65537
    if math.gcd(e, phi) != 1:
        e = 3
        while math.gcd(e, phi) != 1:
            e += 2
    
    d = modinv(e, phi)
    return (e, n), (d, n)

def text_to_int(text):
    return int.from_bytes(text.encode('utf-8'), byteorder='big')

def int_to_text(number):
    byte_length = (number.bit_length() + 7) // 8
    return number.to_bytes(byte_length, byteorder='big').decode('utf-8')

def encrypt_text(message, public_key):
    message_int = text_to_int(message)
    e, n = public_key
    if message_int >= n:
        raise ValueError('Message too long for encryption key size')
    return pow(message_int, e, n)

def decrypt_text(ciphertext, private_key):
    decrypted_int = pow(ciphertext, private_key[0], private_key[1])
    return int_to_text(decrypted_int)
