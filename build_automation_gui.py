#!/usr/bin/env python3

"""
Build Automation GUI
A graphical user interface with buttons for the build automation workflow
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import os
import threading
from pathlib import Path

class BuildAutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Build Automation GUI")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Get script directory
        self.script_dir = Path(__file__).parent.absolute()
        self.build_script = self.script_dir / "build_automation.sh"
        self.config_file = self.script_dir / "build_config.cfg"
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create main container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Build Automation Control Panel", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # Configuration frame
        self.create_config_frame(main_frame)
        
        # Action buttons frame
        self.create_action_buttons(main_frame)
        
        # Combined actions frame
        self.create_combined_actions(main_frame)
        
        # Log output frame
        self.create_log_frame(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Load initial config
        self.load_config_info()
    
    def create_config_frame(self, parent):
        """Create configuration display and selection frame"""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Config file
        ttk.Label(config_frame, text="Config File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.config_label = ttk.Label(config_frame, text=str(self.config_file), 
                                     foreground="blue")
        self.config_label.grid(row=0, column=1, sticky=tk.W)
        
        btn_select = ttk.Button(config_frame, text="Select Config", 
                               command=self.select_config)
        btn_select.grid(row=0, column=2, padx=(10, 0))
        
        btn_view = ttk.Button(config_frame, text="View Config", 
                             command=self.view_config)
        btn_view.grid(row=0, column=3, padx=(5, 0))
        
        # Project info
        ttk.Label(config_frame, text="Project:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.project_label = ttk.Label(config_frame, text="Loading...")
        self.project_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Build type
        ttk.Label(config_frame, text="Build Type:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.build_type_label = ttk.Label(config_frame, text="Loading...")
        self.build_type_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
    
    def create_action_buttons(self, parent):
        """Create main action buttons"""
        actions_frame = ttk.LabelFrame(parent, text="Individual Operations", padding="10")
        actions_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Configure grid
        for i in range(5):
            actions_frame.columnconfigure(i, weight=1)
        
        # Define buttons
        buttons = [
            ("Update APP_ROOT", "-u", "Update APP_ROOT in AppConfig.sh", 0, 0),
            ("Build Project", "-b", "Build (compile) the project", 0, 1),
            ("Generate Package", "-g", "Generate deployment package", 0, 2),
            ("Deploy to Setup", "-d", "Deploy to setup", 0, 3),
            ("Install on Setup", "-i", "Install on setup", 0, 4),
        ]
        
        for text, options, tooltip, row, col in buttons:
            btn = ttk.Button(actions_frame, text=text, 
                           command=lambda o=options, t=text: self.execute_command(o, t))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
            # Add tooltip (simplified)
            self.create_tooltip(btn, tooltip)
    
    def create_combined_actions(self, parent):
        """Create combined action buttons"""
        combined_frame = ttk.LabelFrame(parent, text="Combined Operations", padding="10")
        combined_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Configure grid
        for i in range(3):
            combined_frame.columnconfigure(i, weight=1)
        
        # Define combined buttons
        buttons = [
            ("Build + Generate", "-b -g", 0, 0),
            ("Generate + Deploy", "-g -d", 0, 1),
            ("Deploy + Install", "-d -i", 0, 2),
            ("Update + Build + Generate", "-u -b -g", 1, 0),
            ("Execute All Steps", "-a", 1, 1),
        ]
        
        for text, options, row, col in buttons:
            btn = ttk.Button(combined_frame, text=text,
                           command=lambda o=options, t=text: self.execute_command(o, t),
                           style='Accent.TButton' if options == '-a' else 'TButton')
            btn.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
    
    def create_log_frame(self, parent):
        """Create log output frame"""
        log_frame = ttk.LabelFrame(parent, text="Execution Log", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text widget
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        btn_clear = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        btn_clear.grid(row=1, column=0, pady=(5, 0))
    
    def create_tooltip(self, widget, text):
        """Create a simple tooltip"""
        def on_enter(event):
            self.status_var.set(text)
        def on_leave(event):
            self.status_var.set("Ready")
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def load_config_info(self):
        """Load and display configuration information"""
        try:
            if self.config_file.exists():
                config_data = {}
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config_data[key.strip()] = value.strip()
                
                self.project_label.config(text=config_data.get('PROJECT_NAME', 'N/A'))
                self.build_type_label.config(text=config_data.get('BUILD_TYPE', 'N/A'))
            else:
                self.project_label.config(text="Config file not found")
                self.build_type_label.config(text="N/A")
        except Exception as e:
            self.log_message(f"Error loading config: {str(e)}", "error")
    
    def select_config(self):
        """Open file dialog to select config file"""
        filename = filedialog.askopenfilename(
            title="Select Configuration File",
            initialdir=self.script_dir,
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = Path(filename)
            self.config_label.config(text=str(self.config_file))
            self.load_config_info()
            messagebox.showinfo("Success", f"Configuration file set to:\n{self.config_file}")
    
    def view_config(self):
        """Display config file contents"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Create a new window
            view_window = tk.Toplevel(self.root)
            view_window.title("Configuration File")
            view_window.geometry("700x500")
            
            text_widget = scrolledtext.ScrolledText(view_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, content)
            text_widget.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Error", f"Configuration file not found:\n{self.config_file}")
    
    def log_message(self, message, msg_type="info"):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.update()
    
    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)
    
    def execute_command(self, options, description):
        """Execute build automation command"""
        # Confirm action
        if not messagebox.askyesno("Confirm", f"Execute: {description}?"):
            return
        
        # Check if build script exists
        if not self.build_script.exists():
            messagebox.showerror("Error", f"Build script not found:\n{self.build_script}")
            return
        
        # Disable all buttons during execution
        self.disable_all_buttons()
        
        # Update status
        self.status_var.set(f"Executing: {description}...")
        self.log_message(f"\n{'='*60}")
        self.log_message(f"Executing: {description}")
        self.log_message(f"Config: {self.config_file}")
        self.log_message(f"Command: {self.build_script} -c {self.config_file} {options}")
        self.log_message(f"{'='*60}\n")
        
        # Execute in separate thread
        thread = threading.Thread(target=self.run_command, args=(options, description))
        thread.daemon = True
        thread.start()
    
    def run_command(self, options, description):
        """Run the command in a separate thread"""
        try:
            cmd = [str(self.build_script), "-c", str(self.config_file)] + options.split()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line
            for line in process.stdout:
                self.root.after(0, self.log_message, line.rstrip())
            
            process.wait()
            
            # Show result
            if process.returncode == 0:
                self.root.after(0, self.show_success, description)
            else:
                self.root.after(0, self.show_error, description, process.returncode)
        
        except Exception as e:
            self.root.after(0, self.show_error, description, str(e))
        
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_all_buttons)
            self.root.after(0, self.status_var.set, "Ready")
    
    def show_success(self, description):
        """Show success message"""
        self.log_message(f"\n✓ {description} completed successfully!\n")
        messagebox.showinfo("Success", f"{description} completed successfully!")
    
    def show_error(self, description, error):
        """Show error message"""
        self.log_message(f"\n✗ {description} failed: {error}\n")
        messagebox.showerror("Error", f"{description} failed!\n\nError: {error}")
    
    def disable_all_buttons(self):
        """Disable all buttons during execution"""
        for widget in self.root.winfo_children():
            self.disable_widget_recursive(widget)
    
    def enable_all_buttons(self):
        """Enable all buttons after execution"""
        for widget in self.root.winfo_children():
            self.enable_widget_recursive(widget)
    
    def disable_widget_recursive(self, widget):
        """Recursively disable widgets"""
        if isinstance(widget, ttk.Button):
            widget.state(['disabled'])
        for child in widget.winfo_children():
            self.disable_widget_recursive(child)
    
    def enable_widget_recursive(self, widget):
        """Recursively enable widgets"""
        if isinstance(widget, ttk.Button):
            widget.state(['!disabled'])
        for child in widget.winfo_children():
            self.enable_widget_recursive(child)

def main():
    root = tk.Tk()
    app = BuildAutomationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
