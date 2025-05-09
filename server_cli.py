import socket
import threading
import json
import pickle
import time
import sys
from rsa import generate_keys, encrypt_text, decrypt_text

class Server:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_id: (connection, address, public_key)}
        self.client_counter = 0
        self.public_key, self.private_key = generate_keys(bit_length=512)
        self.running = True
        
    def start(self):
        """Start the server and listen for incoming connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Server started on {self.host}:{self.port}")
            print(f"Server public key: {self.public_key}")
            
            # Start a thread for server input
            input_thread = threading.Thread(target=self.handle_server_input)
            input_thread.daemon = True
            input_thread.start()
            
            # Accept client connections
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_id = self.client_counter
                    self.client_counter += 1
                    
                    # Start a thread to handle this client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address, client_id)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                        
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.shutdown()
    
    def handle_client(self, client_socket, address, client_id):
        """Handle communication with a connected client."""
        print(f"New connection from {address}, assigned ID: {client_id}")
        
        try:
            # Send server's public key to client
            public_key_data = pickle.dumps(self.public_key)
            client_socket.send(public_key_data)
            
            # Receive client's public key
            client_public_key_data = client_socket.recv(4096)
            client_public_key = pickle.loads(client_public_key_data)
            
            # Add client to the clients dictionary
            self.clients[client_id] = (client_socket, address, client_public_key)
            
            # Welcome message
            welcome_msg = f"Welcome! You are connected as client #{client_id}"
            encrypted_welcome = encrypt_text(welcome_msg, client_public_key)
            message_data = {
                'sender': 'server',
                'encrypted_message': encrypted_welcome
            }
            client_socket.send(pickle.dumps(message_data))
            
            # Broadcast that a new client has joined
            self.broadcast(f"Client #{client_id} has joined the server!", exclude_client=None)
            
            # Start receiving messages from this client
            while self.running:
                try:
                    # Receive encrypted message
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    message_data = pickle.loads(data)
                    encrypted_message = message_data.get('encrypted_message')
                    
                    # Decrypt the message
                    decrypted_message = decrypt_text(encrypted_message, self.private_key)
                    print(f"Message from Client #{client_id}: {decrypted_message}")
                    
                    # Forward message to all other clients
                    self.broadcast(decrypted_message, sender_id=client_id)
                    
                except ConnectionResetError:
                    break
                except Exception as e:
                    print(f"Error receiving message from client #{client_id}: {e}")
                    break
        
        except Exception as e:
            print(f"Error handling client #{client_id}: {e}")
        
        finally:
            # Clean up when client disconnects
            if client_id in self.clients:
                del self.clients[client_id]
                print(f"Client #{client_id} disconnected")
                self.broadcast(f"Client #{client_id} has left the server.", exclude_client=None)
            
            client_socket.close()
    
    def broadcast(self, message, sender_id=None, exclude_client=None):
        """Send a message to all connected clients except the sender."""
        sender_name = f"Client #{sender_id}" if sender_id is not None else "Server"
        formatted_message = f"{sender_name}: {message}"
        
        for client_id, (client_socket, _, client_public_key) in self.clients.items():
            if exclude_client is not None and client_id == exclude_client:
                continue
                
            try:
                # Encrypt message with client's public key
                encrypted_message = encrypt_text(formatted_message, client_public_key)
                message_data = {
                    'sender': 'server' if sender_id is None else f"client_{sender_id}",
                    'encrypted_message': encrypted_message
                }
                client_socket.send(pickle.dumps(message_data))
            except Exception as e:
                print(f"Error broadcasting to client #{client_id}: {e}")
    
    def handle_server_input(self):
        """Handle input from the server console."""
        print("Server is ready to send messages. Type your message and press Enter.")
        
        while self.running:
            message = input("")
            if message.lower() == '/quit':
                print("Shutting down server...")
                self.running = False
                self.server_socket.close()
                break
            elif message.lower() == '/clients':
                print(f"Connected clients: {list(self.clients.keys())}")
            elif message:
                self.broadcast(message)
    
    def shutdown(self):
        """Shutdown the server and close all connections."""
        self.running = False
        
        # Close all client connections
        for client_id, (client_socket, _, _) in list(self.clients.items()):
            try:
                client_socket.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Server has been shut down.")

if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("Server interrupted by user.")
        server.shutdown()
    except Exception as e:
        print(f"Unexpected error: {e}")
        server.shutdown()
