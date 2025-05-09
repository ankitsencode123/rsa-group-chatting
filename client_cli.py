import socket
import threading
import json
import pickle
import time
import sys
from rsa import generate_keys, encrypt_text, decrypt_text

class Client:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.client_socket = None
        self.public_key, self.private_key = generate_keys(bit_length=512)
        self.server_public_key = None
        self.running = True
        self.connected = False
    
    def connect(self):
        """Connect to the server and start communication."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to server at {self.host}:{self.port}")
            print(f"Client public key: {self.public_key}")
            
            # Receive server's public key
            server_public_key_data = self.client_socket.recv(4096)
            self.server_public_key = pickle.loads(server_public_key_data)
            print(f"Received server public key: {self.server_public_key}")
            
            # Send our public key to the server
            self.client_socket.send(pickle.dumps(self.public_key))
            
            # Start receiving messages from server in a separate thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Start sending messages
            self.send_messages()
            
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.disconnect()
    
    def receive_messages(self):
        """Receive and decrypt messages from the server."""
        while self.running and self.connected:
            try:
                # Receive encrypted message from server
                data = self.client_socket.recv(4096)
                
                if not data:
                    print("Server connection closed.")
                    self.disconnect()
                    break
                
                message_data = pickle.loads(data)
                encrypted_message = message_data.get('encrypted_message')
                
                # Decrypt the message using our private key
                decrypted_message = decrypt_text(encrypted_message, self.private_key)
                print(f"\n{decrypted_message}")
                print("You: ", end="", flush=True)  # Restore user prompt
                
            except ConnectionResetError:
                print("\nServer connection was reset.")
                self.disconnect()
                break
            except Exception as e:
                print(f"\nError receiving message: {e}")
                self.disconnect()
                break
    
    def send_messages(self):
        """Send encrypted messages to the server."""
        print("You can now send messages. Type your message and press Enter. Type '/quit' to exit.")
        
        while self.running and self.connected:
            try:
                message = input("You: ")
                
                if message.lower() == '/quit':
                    print("Disconnecting from server...")
                    self.disconnect()
                    break
                
                if message and self.server_public_key:
                    # Encrypt message with server's public key
                    encrypted_message = encrypt_text(message, self.server_public_key)
                    message_data = {
                        'encrypted_message': encrypted_message
                    }
                    self.client_socket.send(pickle.dumps(message_data))
            
            except EOFError:
                # Handle Ctrl+D (EOF) gracefully
                print("\nDisconnecting from server...")
                self.disconnect()
                break
            except Exception as e:
                print(f"Error sending message: {e}")
                self.disconnect()
                break
    
    def disconnect(self):
        """Disconnect from the server and clean up."""
        self.running = False
        self.connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            finally:
                self.client_socket = None
        
        print("Disconnected from server.")

if __name__ == "__main__":
    # Get server details from command line args or use defaults
    host = '192.168.236.135'
    port = 12345
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number: {sys.argv[2]}. Using default: 9999")
    
    client = Client(host, port)
    try:
        client.connect()
    except KeyboardInterrupt:
        print("\nClient interrupted by user.")
        client.disconnect()
    except Exception as e:
        print(f"Unexpected error: {e}")
        client.disconnect()
