import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import socket
import pickle
import sys
import os
from datetime import datetime

# Import from the local rsa.py module
from rsa import generate_keys, encrypt_text, decrypt_text

class ChatServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Chat Server")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Server variables
        self.host = tk.StringVar(value="0.0.0.0")
        self.port = tk.IntVar(value=12345)
        self.server_socket = None
        self.clients = {}  # {client_id: (connection, address, public_key)}
        self.client_counter = 0
        self.running = False
        
        # Generate RSA keys
        self.public_key, self.private_key = generate_keys(bit_length=512)
        
        # Create GUI components
        self.create_widgets()
        
        # Initial status update
        self.update_status("Stopped", "red")
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Server control frame (top)
        server_frame = ttk.LabelFrame(main_frame, text="Server Control", padding=10)
        server_frame.pack(fill=tk.X, pady=5)
        
        # Bind address
        ttk.Label(server_frame, text="Bind Address:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(server_frame, textvariable=self.host, width=15).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Port
        ttk.Label(server_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Entry(server_frame, textvariable=self.port, width=6).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Start/Stop button
        self.server_btn = ttk.Button(server_frame, text="Start Server", command=self.toggle_server)
        self.server_btn.grid(row=0, column=4, padx=10)
        
        # Status indicator
        ttk.Label(server_frame, text="Status:").grid(row=0, column=5, sticky=tk.W, padx=5)
        self.status_label = ttk.Label(server_frame, text="Stopped", foreground="red")
        self.status_label.grid(row=0, column=6, sticky=tk.W, padx=5)
        
        # Client list frame (left side)
        client_frame = ttk.LabelFrame(main_frame, text="Connected Clients", padding=10)
        client_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Create client list
        self.client_listbox = tk.Listbox(client_frame, width=20, height=15)
        self.client_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Chat display and message area (right side)
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=5)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED, height=20)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Message input
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.message_input.bind("<Return>", self.send_broadcast)
        self.message_input.config(state=tk.DISABLED)
        
        self.send_btn = ttk.Button(input_frame, text="Broadcast", command=self.send_broadcast)
        self.send_btn.pack(side=tk.RIGHT, padx=5)
        self.send_btn.config(state=tk.DISABLED)
    
    def update_status(self, status, color):
        self.status_label.config(text=status, foreground=color)
    
    def append_message(self, message, tag=None):
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        
        # Insert timestamp
        self.chat_display.insert(tk.END, timestamp, "timestamp")
        
        # Insert message with appropriate tag
        self.chat_display.insert(tk.END, message + "\n", tag)
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def update_client_list(self):
        """Update the client list display"""
        self.client_listbox.delete(0, tk.END)
        for client_id in sorted(self.clients.keys()):
            _, address, _ = self.clients[client_id]
            self.client_listbox.insert(tk.END, f"Client #{client_id} ({address[0]})")
    
    def toggle_server(self):
        """Start or stop the server"""
        if self.running:
            self.stop_server()
        else:
            self.start_server()
    
    def start_server(self):
        """Start the server and listen for connections"""
        if self.running:
            return
        
        try:
            host = self.host.get()
            port = self.port.get()
            
            # Create and configure server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.settimeout(0.5)  # Add timeout for clean shutdown
            self.server_socket.listen(5)
            
            # Update UI
            self.running = True
            self.update_status("Running", "green")
            self.server_btn.config(text="Stop Server")
            self.message_input.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            
            # Log server start
            self.append_message(f"Server started on {host}:{port}", "system")
            self.append_message(f"Server public key: {self.public_key}", "system")
            
            # Start accepting clients in a separate thread
            accept_thread = threading.Thread(target=self.accept_clients)
            accept_thread.daemon = True
            accept_thread.start()
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
            self.stop_server()
    
    def stop_server(self):
        """Stop the server and disconnect all clients"""
        self.running = False
        
        # Close all client connections
        for client_id, (client_socket, _, _) in list(self.clients.items()):
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # Update UI
        self.update_status("Stopped", "red")
        self.server_btn.config(text="Start Server")
        self.message_input.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.update_client_list()
        
        # Log server stop
        self.append_message("Server stopped", "system")
    
    def accept_clients(self):
        """Accept incoming client connections"""
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
                
            except socket.timeout:
                continue  # Just a timeout for clean shutdown checking
            except Exception as e:
                if self.running:
                    self.root.after(0, self.append_message, f"Error accepting connection: {str(e)}", "error")
    
    def handle_client(self, client_socket, address, client_id):
        """Handle communication with a connected client"""
        try:
            # Send server's public key to client
            public_key_data = pickle.dumps(self.public_key)
            client_socket.send(public_key_data)
            
            # Receive client's public key
            client_public_key_data = client_socket.recv(4096)
            client_public_key = pickle.loads(client_public_key_data)
            
            # Add client to the clients dictionary
            self.clients[client_id] = (client_socket, address, client_public_key)
            
            # Update UI in main thread
            self.root.after(0, self.append_message, f"New connection from {address}, assigned ID: {client_id}", "system")
            self.root.after(0, self.update_client_list)
            
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
                    
                    # Display message in UI
                    display_msg = f"Client #{client_id}: {decrypted_message}"
                    self.root.after(0, self.append_message, display_msg, "client")
                    
                    # Forward message to all other clients
                    self.broadcast(decrypted_message, sender_id=client_id)
                    
                except ConnectionResetError:
                    break
                except Exception as e:
                    self.root.after(0, self.append_message, f"Error receiving from client #{client_id}: {str(e)}", "error")
                    break
                
        except Exception as e:
            self.root.after(0, self.append_message, f"Error handling client #{client_id}: {str(e)}", "error")
        
        finally:
            # Clean up when client disconnects
            if client_id in self.clients:
                del self.clients[client_id]
                self.root.after(0, self.append_message, f"Client #{client_id} disconnected", "system")
                self.root.after(0, self.update_client_list)
                self.broadcast(f"Client #{client_id} has left the server.", exclude_client=None)
            
            client_socket.close()
    
    def broadcast(self, message, sender_id=None, exclude_client=None):
        """Send a message to all connected clients except the sender."""
        if not self.clients:
            return
            
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
                self.root.after(0, self.append_message, f"Error broadcasting to client #{client_id}: {str(e)}", "error")
    
    def send_broadcast(self, event=None):
        """Send a broadcast message from the server to all clients"""
        if not self.running or not self.clients:
            return
            
        message = self.message_input.get().strip()
        if not message:
            return
            
        try:
            # Clear the input field
            self.message_input.delete(0, tk.END)
            
            # Display in server log
            self.append_message(f"Server: {message}", "server")
            
            # Broadcast to all clients
            self.broadcast(message)
            
        except Exception as e:
            messagebox.showerror("Broadcast Error", f"Failed to broadcast message: {str(e)}")
    
    def on_closing(self):
        """Handle window closing"""
        if self.running:
            self.stop_server()
        self.root.destroy()

def main():
    root = tk.Tk()
    
    # Configure tags and styles
    style = ttk.Style()
    style.configure("TButton", padding=6)
    style.configure("TLabel", padding=3)
    
    # Create app
    app = ChatServerGUI(root)
    
    # Set up text tags for coloring
    app.chat_display.tag_configure("timestamp", foreground="gray")
    app.chat_display.tag_configure("system", foreground="blue")
    app.chat_display.tag_configure("server", foreground="green")
    app.chat_display.tag_configure("client", foreground="black")
    app.chat_display.tag_configure("error", foreground="red")
    
    root.mainloop()

if __name__ == "__main__":
    main()
