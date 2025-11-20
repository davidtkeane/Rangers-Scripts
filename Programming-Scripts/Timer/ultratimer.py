#!/usr/bin/env python3
"""
UltraTimer - Professional Desktop Timer/Clock/Countdown
Author: David's Custom Timer
Works on: MacOS (M1/M2/M3), Windows, Linux
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time
from datetime import datetime, timedelta
import threading
import platform
import os
from pathlib import Path
import pygame  # For sound effects
from dataclasses import dataclass
from typing import Dict, List, Optional
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# Initialize pygame for sound
pygame.mixer.init()

@dataclass
class TimerPreset:
    """Store timer presets"""
    name: str
    duration: int  # in seconds
    warning_time: int = 120  # 2 minutes warning
    critical_time: int = 60  # 1 minute critical
    sound_enabled: bool = True
    color_theme: str = "default"

class UltraTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UltraTimer Pro")
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        # Platform-specific transparency
        if platform.system() == "Darwin":  # macOS
            self.root.attributes('-transparent', True)
        elif platform.system() == "Windows":
            self.root.attributes('-alpha', 0.95)
        else:  # Linux
            self.root.wait_visibility(self.root)
            self.root.attributes('-alpha', 0.95)
        
        # Variables
        self.mode = tk.StringVar(value="clock")  # clock, timer, countdown, stopwatch, pomodoro
        self.is_running = False
        self.start_time = 0
        self.duration = 300  # 5 minutes default
        self.elapsed = 0
        self.remaining = 0
        
        # Appearance settings
        self.is_minimal = False
        self.transparency = tk.DoubleVar(value=0.95)
        self.always_on_top = tk.BooleanVar(value=True)
        self.click_through = tk.BooleanVar(value=False)
        
        # Color schemes
        self.themes = {
            "default": {"bg": "#1a1a2e", "fg": "#eee", "accent": "#16f4d0"},
            "dark": {"bg": "#000", "fg": "#0f0", "accent": "#f00"},
            "light": {"bg": "#fff", "fg": "#000", "accent": "#007acc"},
            "neon": {"bg": "#0a0a0a", "fg": "#ff00ff", "accent": "#00ffff"},
            "forest": {"bg": "#1b4332", "fg": "#d8f3dc", "accent": "#52b788"},
            "ocean": {"bg": "#006494", "fg": "#e8f4fd", "accent": "#00a6fb"},
            "sunset": {"bg": "#832161", "fg": "#ffd23f", "accent": "#ee4266"}
        }
        self.current_theme = "default"
        
        # Presets storage
        self.presets_file = Path.home() / ".ultratimer_presets.json"
        self.presets = self.load_presets()
        
        # Sound files (create these or download)
        self.sounds = {
            "warning": "warning.mp3",
            "critical": "critical.mp3", 
            "finish": "finish.mp3",
            "tick": "tick.mp3"
        }
        
        # Statistics tracking
        self.stats = {
            "total_sessions": 0,
            "total_time": 0,
            "completed_timers": 0,
            "average_duration": 0
        }
        self.stats_file = Path.home() / ".ultratimer_stats.json"
        self.load_stats()
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Start web server for remote control (optional)
        self.start_web_server()
        
        # Start update loop
        self.update_display()
        
    def setup_ui(self):
        """Build the user interface"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg=self.themes[self.current_theme]["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top bar with mode selector
        self.top_bar = tk.Frame(self.main_frame, bg=self.themes[self.current_theme]["bg"])
        self.top_bar.pack(fill=tk.X, pady=(0, 10))
        
        modes = ["Clock", "Timer", "Countdown", "Stopwatch", "Pomodoro"]
        for mode in modes:
            btn = tk.Button(
                self.top_bar,
                text=mode,
                command=lambda m=mode.lower(): self.switch_mode(m),
                bg=self.themes[self.current_theme]["accent"],
                fg=self.themes[self.current_theme]["bg"],
                font=("Arial", 10, "bold"),
                relief=tk.FLAT,
                padx=10
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Settings button
        settings_btn = tk.Button(
            self.top_bar,
            text="⚙",
            command=self.open_settings,
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"],
            font=("Arial", 14),
            relief=tk.FLAT
        )
        settings_btn.pack(side=tk.RIGHT)
        
        # Main display
        self.display_frame = tk.Frame(self.main_frame, bg=self.themes[self.current_theme]["bg"])
        self.display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.time_display = tk.Label(
            self.display_frame,
            text="00:00:00",
            font=("Digital-7", 72, "bold"),  # You'll need to install Digital-7 font or use Arial
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"]
        )
        self.time_display.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.display_frame,
            length=300,
            mode='determinate',
            style="timer.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)
        
        # Sub-display (for additional info)
        self.sub_display = tk.Label(
            self.display_frame,
            text="",
            font=("Arial", 14),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"]
        )
        self.sub_display.pack()
        
        # Control buttons
        self.control_frame = tk.Frame(self.main_frame, bg=self.themes[self.current_theme]["bg"])
        self.control_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = tk.Button(
            self.control_frame,
            text="▶ Start",
            command=self.toggle_timer,
            bg=self.themes[self.current_theme]["accent"],
            fg=self.themes[self.current_theme]["bg"],
            font=("Arial", 12, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = tk.Button(
            self.control_frame,
            text="↺ Reset",
            command=self.reset_timer,
            bg=self.themes[self.current_theme]["fg"],
            fg=self.themes[self.current_theme]["bg"],
            font=("Arial", 12, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Quick time buttons
        quick_frame = tk.Frame(self.main_frame, bg=self.themes[self.current_theme]["bg"])
        quick_frame.pack(fill=tk.X, pady=5)
        
        quick_times = [("1m", 60), ("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800)]
        for label, seconds in quick_times:
            btn = tk.Button(
                quick_frame,
                text=label,
                command=lambda s=seconds: self.set_duration(s),
                bg=self.themes[self.current_theme]["bg"],
                fg=self.themes[self.current_theme]["accent"],
                font=("Arial", 10),
                relief=tk.RAISED,
                bd=1,
                padx=8
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_bar = tk.Label(
            self.main_frame,
            text="Ready",
            font=("Arial", 10),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"],
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
        
    def setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts"""
        self.root.bind('<space>', lambda e: self.toggle_timer())
        self.root.bind('r', lambda e: self.reset_timer())
        self.root.bind('m', lambda e: self.toggle_minimal())
        self.root.bind('t', lambda e: self.toggle_transparency())
        self.root.bind('<Escape>', lambda e: self.root.quit())
        self.root.bind('1', lambda e: self.set_duration(60))
        self.root.bind('5', lambda e: self.set_duration(300))
        self.root.bind('0', lambda e: self.set_duration(600))
        
        # Function keys for modes
        self.root.bind('<F1>', lambda e: self.switch_mode('clock'))
        self.root.bind('<F2>', lambda e: self.switch_mode('timer'))
        self.root.bind('<F3>', lambda e: self.switch_mode('countdown'))
        self.root.bind('<F4>', lambda e: self.switch_mode('stopwatch'))
        self.root.bind('<F5>', lambda e: self.switch_mode('pomodoro'))
        
    def switch_mode(self, mode):
        """Switch between different timer modes"""
        self.mode.set(mode)
        self.reset_timer()
        self.status_bar.config(text=f"Mode: {mode.capitalize()}")
        
        if mode == "clock":
            self.show_clock()
        elif mode == "pomodoro":
            self.start_pomodoro()
            
    def show_clock(self):
        """Display current time and date"""
        def update_clock():
            if self.mode.get() == "clock":
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                date_str = now.strftime("%A, %B %d, %Y")
                self.time_display.config(text=time_str)
                self.sub_display.config(text=date_str)
                self.root.after(1000, update_clock)
        update_clock()
        
    def start_pomodoro(self):
        """Start Pomodoro timer (25 min work, 5 min break)"""
        self.duration = 1500  # 25 minutes
        self.sub_display.config(text="Work Session - 25 minutes")
        
    def toggle_timer(self):
        """Start/stop the timer"""
        if self.is_running:
            self.is_running = False
            self.start_btn.config(text="▶ Start")
            self.status_bar.config(text="Paused")
        else:
            self.is_running = True
            self.start_btn.config(text="⏸ Pause")
            self.status_bar.config(text="Running")
            if self.mode.get() == "stopwatch":
                self.start_time = time.time() - self.elapsed
            elif self.mode.get() in ["timer", "countdown", "pomodoro"]:
                self.start_time = time.time()
                
    def reset_timer(self):
        """Reset the timer"""
        self.is_running = False
        self.elapsed = 0
        self.remaining = self.duration
        self.start_btn.config(text="▶ Start")
        self.progress['value'] = 0
        self.update_display()
        self.status_bar.config(text="Reset")
        
    def set_duration(self, seconds):
        """Set timer duration"""
        self.duration = seconds
        self.remaining = seconds
        self.update_display()
        self.status_bar.config(text=f"Duration set to {seconds//60} minutes")
        
    def update_display(self):
        """Update the display based on current mode"""
        if self.mode.get() == "clock":
            pass  # Clock updates itself
        elif self.mode.get() == "stopwatch":
            if self.is_running:
                self.elapsed = time.time() - self.start_time
            hours = int(self.elapsed // 3600)
            minutes = int((self.elapsed % 3600) // 60)
            seconds = int(self.elapsed % 60)
            self.time_display.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
        elif self.mode.get() in ["timer", "countdown", "pomodoro"]:
            if self.is_running:
                elapsed = time.time() - self.start_time
                self.remaining = max(0, self.duration - elapsed)
                
                # Update progress bar
                progress_percent = ((self.duration - self.remaining) / self.duration) * 100
                self.progress['value'] = progress_percent
                
                # Change colors based on time remaining
                if self.remaining <= 60:
                    self.time_display.config(fg="#ff0000")  # Red
                    if self.remaining == 60:
                        self.play_sound("critical")
                elif self.remaining <= 120:
                    self.time_display.config(fg="#ffff00")  # Yellow
                    if self.remaining == 120:
                        self.play_sound("warning")
                else:
                    self.time_display.config(fg=self.themes[self.current_theme]["fg"])
                
                # Check if timer finished
                if self.remaining == 0:
                    self.is_running = False
                    self.play_sound("finish")
                    self.show_notification("Timer Finished!")
                    self.stats["completed_timers"] += 1
                    self.save_stats()
                    
            hours = int(self.remaining // 3600)
            minutes = int((self.remaining % 3600) // 60)
            seconds = int(self.remaining % 60)
            
            if hours > 0:
                self.time_display.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.time_display.config(text=f"{minutes:02d}:{seconds:02d}")
        
        # Schedule next update
        self.root.after(100, self.update_display)  # Update every 100ms for smooth display
        
    def toggle_minimal(self):
        """Toggle between minimal and full view"""
        if self.is_minimal:
            self.top_bar.pack(fill=tk.X, pady=(0, 10))
            self.control_frame.pack(fill=tk.X, pady=10)
            self.status_bar.pack(fill=tk.X, pady=(5, 0))
            self.is_minimal = False
        else:
            self.top_bar.pack_forget()
            self.control_frame.pack_forget()
            self.status_bar.pack_forget()
            self.is_minimal = True
            
    def toggle_transparency(self):
        """Cycle through transparency levels"""
        current = self.transparency.get()
        levels = [0.3, 0.5, 0.7, 0.9, 1.0]
        next_level = levels[(levels.index(min(levels, key=lambda x: abs(x - current))) + 1) % len(levels)]
        self.transparency.set(next_level)
        
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.root.attributes('-alpha', next_level)
        
    def open_settings(self):
        """Open settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x500")
        settings_window.attributes('-topmost', True)
        
        # Theme selector
        tk.Label(settings_window, text="Theme:", font=("Arial", 12, "bold")).pack(pady=10)
        for theme_name in self.themes.keys():
            btn = tk.Button(
                settings_window,
                text=theme_name.capitalize(),
                command=lambda t=theme_name: self.change_theme(t),
                width=15
            )
            btn.pack(pady=2)
        
        # Sound toggle
        self.sound_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_window,
            text="Enable Sounds",
            variable=self.sound_enabled,
            font=("Arial", 11)
        ).pack(pady=20)
        
        # Always on top toggle
        tk.Checkbutton(
            settings_window,
            text="Always on Top",
            variable=self.always_on_top,
            command=self.toggle_always_on_top,
            font=("Arial", 11)
        ).pack(pady=5)
        
        # Preset management
        tk.Label(settings_window, text="Presets:", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Save current as preset
        tk.Button(
            settings_window,
            text="Save Current Timer as Preset",
            command=self.save_preset,
            width=25
        ).pack(pady=5)
        
        # Load preset
        tk.Button(
            settings_window,
            text="Load Preset",
            command=self.load_preset,
            width=25
        ).pack(pady=5)
        
        # Statistics
        tk.Label(settings_window, text="Statistics:", font=("Arial", 12, "bold")).pack(pady=10)
        stats_text = f"""
        Total Sessions: {self.stats['total_sessions']}
        Completed Timers: {self.stats['completed_timers']}
        Total Time: {self.stats['total_time'] // 3600}h {(self.stats['total_time'] % 3600) // 60}m
        """
        tk.Label(settings_window, text=stats_text, font=("Arial", 10)).pack()
        
        # Export/Import buttons
        tk.Button(
            settings_window,
            text="Export Settings",
            command=self.export_settings,
            width=25
        ).pack(pady=5)
        
        tk.Button(
            settings_window,
            text="Import Settings",
            command=self.import_settings,
            width=25
        ).pack(pady=5)
        
    def change_theme(self, theme_name):
        """Change the color theme"""
        self.current_theme = theme_name
        theme = self.themes[theme_name]
        
        # Update all widgets with new colors
        self.main_frame.config(bg=theme["bg"])
        self.top_bar.config(bg=theme["bg"])
        self.display_frame.config(bg=theme["bg"])
        self.control_frame.config(bg=theme["bg"])
        self.time_display.config(bg=theme["bg"], fg=theme["fg"])
        self.sub_display.config(bg=theme["bg"], fg=theme["fg"])
        self.status_bar.config(bg=theme["bg"], fg=theme["fg"])
        
    def toggle_always_on_top(self):
        """Toggle always on top window attribute"""
        self.root.attributes('-topmost', self.always_on_top.get())
        
    def play_sound(self, sound_type):
        """Play a sound effect"""
        if not self.sound_enabled.get():
            return
            
        # For now, use system beep. You can add actual sound files
        if platform.system() == "Darwin":  # macOS
            os.system("afplay /System/Library/Sounds/Glass.aiff")
        elif platform.system() == "Windows":
            import winsound
            winsound.Beep(1000, 200)
        else:  # Linux
            os.system("paplay /usr/share/sounds/freedesktop/stereo/complete.oga")
            
    def show_notification(self, message):
        """Show system notification"""
        if platform.system() == "Darwin":  # macOS
            os.system(f"""
                osascript -e 'display notification "{message}" with title "UltraTimer"'
            """)
        elif platform.system() == "Windows":
            messagebox.showinfo("UltraTimer", message)
        else:  # Linux
            os.system(f'notify-send "UltraTimer" "{message}"')
            
    def save_preset(self):
        """Save current timer configuration as preset"""
        name = tk.simpledialog.askstring("Save Preset", "Enter preset name:")
        if name:
            preset = TimerPreset(
                name=name,
                duration=self.duration,
                sound_enabled=self.sound_enabled.get(),
                color_theme=self.current_theme
            )
            self.presets[name] = preset
            self.save_presets()
            self.status_bar.config(text=f"Preset '{name}' saved")
            
    def load_preset(self):
        """Load a saved preset"""
        if not self.presets:
            messagebox.showinfo("No Presets", "No saved presets found")
            return
            
        # Create preset selection window
        preset_window = tk.Toplevel(self.root)
        preset_window.title("Load Preset")
        preset_window.geometry("300x400")
        
        for name, preset in self.presets.items():
            btn = tk.Button(
                preset_window,
                text=f"{name} ({preset.duration//60} min)",
                command=lambda p=preset: self.apply_preset(p),
                width=30
            )
            btn.pack(pady=2)
            
    def apply_preset(self, preset):
        """Apply a preset configuration"""
        self.duration = preset.duration
        self.remaining = preset.duration
        self.sound_enabled.set(preset.sound_enabled)
        self.change_theme(preset.color_theme)
        self.update_display()
        self.status_bar.config(text=f"Loaded preset: {preset.name}")
        
    def save_presets(self):
        """Save presets to file"""
        with open(self.presets_file, 'w') as f:
            json.dump(
                {name: vars(preset) for name, preset in self.presets.items()},
                f,
                indent=2
            )
            
    def load_presets(self):
        """Load presets from file"""
        if self.presets_file.exists():
            with open(self.presets_file, 'r') as f:
                data = json.load(f)
                return {
                    name: TimerPreset(**preset_data)
                    for name, preset_data in data.items()
                }
        return {}
        
    def save_stats(self):
        """Save statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
            
    def load_stats(self):
        """Load statistics from file"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                self.stats = json.load(f)
                
    def export_settings(self):
        """Export all settings to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            settings = {
                "presets": {name: vars(preset) for name, preset in self.presets.items()},
                "stats": self.stats,
                "theme": self.current_theme,
                "sound_enabled": self.sound_enabled.get()
            }
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            self.status_bar.config(text=f"Settings exported to {filename}")
            
    def import_settings(self):
        """Import settings from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            # Apply imported settings
            self.presets = {
                name: TimerPreset(**preset_data)
                for name, preset_data in settings.get("presets", {}).items()
            }
            self.stats = settings.get("stats", self.stats)
            self.change_theme(settings.get("theme", "default"))
            self.sound_enabled.set(settings.get("sound_enabled", True))
            
            self.save_presets()
            self.save_stats()
            self.status_bar.config(text="Settings imported successfully")
            
    def start_web_server(self):
        """Start web server for remote control"""
        def run_server():
            try:
                # Create simple HTML remote control
                html_content = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>UltraTimer Remote</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            background: #1a1a2e;
                            color: #eee;
                            text-align: center;
                            padding: 20px;
                        }
                        button {
                            background: #16f4d0;
                            color: #1a1a2e;
                            border: none;
                            padding: 15px 30px;
                            margin: 10px;
                            font-size: 18px;
                            border-radius: 5px;
                            cursor: pointer;
                        }
                        button:hover {
                            background: #13c4a8;
                        }
                        h1 {
                            color: #16f4d0;
                        }
                        .time-display {
                            font-size: 48px;
                            font-weight: bold;
                            margin: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1>UltraTimer Remote Control</h1>
                    <div class="time-display" id="time">00:00</div>
                    <div>
                        <button onclick="sendCommand('start')">Start/Pause</button>
                        <button onclick="sendCommand('reset')">Reset</button>
                    </div>
                    <div>
                        <button onclick="sendCommand('1min')">1 Min</button>
                        <button onclick="sendCommand('5min')">5 Min</button>
                        <button onclick="sendCommand('10min')">10 Min</button>
                    </div>
                    <script>
                        function sendCommand(cmd) {
                            fetch('/command/' + cmd);
                        }
                        setInterval(() => {
                            fetch('/status').then(r => r.json()).then(data => {
                                document.getElementById('time').innerText = data.time;
                            });
                        }, 1000);
                    </script>
                </body>
                </html>
                """
                
                # Find available port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', 0))
                port = sock.getsockname()[1]
                sock.close()
                
                # Save HTML to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(html_content)
                    temp_html = f.name
                
                # Simple HTTP server
                server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
                
                # Show URL in status bar
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                self.status_bar.config(text=f"Remote: http://{ip}:{port}")
                
                # Note: This is a simplified version. 
                # For full functionality, you'd need a proper web framework
                
            except Exception as e:
                print(f"Web server error: {e}")
        
        # Run server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = UltraTimer()
    app.run()