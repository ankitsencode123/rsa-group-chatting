import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os

class Launcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Chat Launcher")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Secure RSA Encrypted Chat", font=("Helvetica", 16))
        title_label.pack(pady=10)
        
        # Description
        desc_label = ttk.Label(main_frame, text="Choose which component to launch:")
        desc_label.pack(pady=10)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Server button
        server_btn = ttk.Button(button_frame, text="Start Server", command=self.start_server)
        server_btn.pack(side=tk.LEFT, padx=10)
        
        # Client button
        client_btn = ttk.Button(button_frame, text="Start Client", command=self.start_client)
        client_btn.pack(side=tk.LEFT, padx=10)
        
    def start_server(self):
        """Start the server GUI"""
        try:
            subprocess.Popen([sys.executable, "server_gui.py"])
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            
    def start_client(self):
        """Start the client GUI"""
        try:
            subprocess.Popen([sys.executable, "client_gui.py"])
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to start client: {str(e)}")

def main():
    root = tk.Tk()
    app = Launcher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
