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

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Chat Client")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Client connection variables
        self.host = tk.StringVar(value="localhost")
        self.port = tk.IntVar(value=12345)
        self.client_socket = None
        self.connected = False
        self.running = True
        
        # Generate RSA keys
        self.public_key, self.private_key = generate_keys(bit_length=512)
        self.server_public_key = None
        
        # Create GUI components
        self.create_widgets()
        
        # Status updates
        self.update_status("Disconnected", "red")
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection frame (top)
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, pady=5)
        
        # Server address
        ttk.Label(conn_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(conn_frame, textvariable=self.host, width=20).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Server port
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Entry(conn_frame, textvariable=self.port, width=6).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        # Status indicator
        ttk.Label(conn_frame, text="Status:").grid(row=0, column=5, sticky=tk.W, padx=5)
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=6, sticky=tk.W, padx=5)
        
        # Chat display
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Chat history
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Message input area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.message_input.bind("<Return>", self.send_message)
        self.message_input.config(state=tk.DISABLED)
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_message)
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
        
    def connect_to_server(self):
        if self.connected:
            self.disconnect_from_server()
            return
        
        try:
            host = self.host.get()
            port = self.port.get()
            
            # Create socket and connect
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            
            # Update UI
            self.update_status("Connected", "green")
            self.connect_btn.config(text="Disconnect")
            self.message_input.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            
            # Receive server's public key
            server_public_key_data = self.client_socket.recv(4096)
            self.server_public_key = pickle.loads(server_public_key_data)
            
            # Send our public key to the server
            self.client_socket.send(pickle.dumps(self.public_key))
            
            # Display connection info
            self.append_message(f"Connected to server at {host}:{port}", "system")
            
            # Start receiving messages
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.update_status("Error", "red")
            
    def disconnect_from_server(self):
        self.connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            
        # Update UI
        self.update_status("Disconnected", "red")
        self.connect_btn.config(text="Connect")
        self.message_input.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.append_message("Disconnected from server", "system")
        
    def receive_messages(self):
        """Receive and decrypt messages from the server."""
        while self.running and self.connected:
            try:
                # Receive encrypted message from server
                data = self.client_socket.recv(4096)
                
                if not data:
                    if self.connected:
                        self.root.after(0, self.handle_disconnect, "Server connection closed")
                    break
                
                message_data = pickle.loads(data)
                encrypted_message = message_data.get('encrypted_message')
                
                # Decrypt the message using our private key
                decrypted_message = decrypt_text(encrypted_message, self.private_key)
                
                # Display the message
                self.root.after(0, self.append_message, decrypted_message, "received")
                
            except ConnectionResetError:
                if self.connected:
                    self.root.after(0, self.handle_disconnect, "Server connection was reset")
                break
            except Exception as e:
                if self.connected:
                    self.root.after(0, self.handle_disconnect, f"Error receiving: {str(e)}")
                break
    
    def handle_disconnect(self, message):
        """Handle disconnection with a message in the GUI thread"""
        self.append_message(message, "system")
        self.disconnect_from_server()
    
    def send_message(self, event=None):
        """Send encrypted messages to the server."""
        if not self.connected or not self.server_public_key:
            return
        
        message = self.message_input.get().strip()
        if not message:
            return
        
        try:
            # Clear input field
            self.message_input.delete(0, tk.END)
            
            # Display the message we're sending
            self.append_message(f"You: {message}", "sent")
            
            # Encrypt message with server's public key
            encrypted_message = encrypt_text(message, self.server_public_key)
            message_data = {
                'encrypted_message': encrypted_message
            }
            self.client_socket.send(pickle.dumps(message_data))
            
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send message: {str(e)}")
            self.disconnect_from_server()
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        if self.connected:
            self.disconnect_from_server()
        self.root.destroy()

def main():
    root = tk.Tk()
    
    # Configure tags and styles
    style = ttk.Style()
    style.configure("TButton", padding=6)
    style.configure("TLabel", padding=3)
    
    # Create app
    app = ChatClientGUI(root)
    
    # Set up text tags
    app.chat_display.tag_configure("timestamp", foreground="gray")
    app.chat_display.tag_configure("system", foreground="blue")
    app.chat_display.tag_configure("sent", foreground="green")
    app.chat_display.tag_configure("received", foreground="black")
    
    root.mainloop()

if __name__ == "__main__":
    main()
