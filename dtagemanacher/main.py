#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import sys
import os
import math
import json
from typing import List, Optional
from PIL import ImageTk, Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_monitor import get_process_monitor
from types_def import ProcessInfo, ViewMode, AppSettings, CarouselStyle
import window_helper
from mouse_hook import MouseHook

CONFIG_FILE = "config.json"

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings: AppSettings, on_save_callback):
        super().__init__(parent)
        self.title("Visual Settings")
        self.geometry("400x550")
        self.resizable(False, False)
        self.settings = settings
        self.callback = on_save_callback
        
        self.attributes('-topmost', True)
        
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.focus_force()
        
        style = ttk.Style()
        style.configure("TLabel", padding=5)
        style.configure("TButton", padding=5)
        
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Animation Speed (Lower is faster):").pack(fill=tk.X)
        self.speed_var = tk.DoubleVar(value=self.settings.animation_speed)
        scale = ttk.Scale(main_frame, from_=0.01, to=0.5, variable=self.speed_var)
        scale.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="Flip3D Spacing:").pack(fill=tk.X)
        self.spacing_var = tk.IntVar(value=self.settings.flip3d_spacing)
        scale_spacing = ttk.Scale(main_frame, from_=50, to=400, variable=self.spacing_var)
        scale_spacing.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="Thumbnail Scale:").pack(fill=tk.X)
        self.scale_var = tk.DoubleVar(value=self.settings.flip3d_card_scale)
        scale_scale = ttk.Scale(main_frame, from_=0.5, to=2.0, variable=self.scale_var)
        scale_scale.pack(fill=tk.X, pady=5)
        
        self.mem_var = tk.BooleanVar(value=self.settings.show_memory_on_thumbnails)
        ttk.Checkbutton(main_frame, text="Show Memory Usage", variable=self.mem_var).pack(fill=tk.X, pady=5)

        self.borders_var = tk.BooleanVar(value=self.settings.show_borders)
        ttk.Checkbutton(main_frame, text="Show Card Borders/Frames", variable=self.borders_var).pack(fill=tk.X, pady=5)

        self.titles_var = tk.BooleanVar(value=self.settings.show_titles)
        ttk.Checkbutton(main_frame, text="Show Window Titles", variable=self.titles_var).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Default View Mode:").pack(fill=tk.X)
        self.view_var = tk.StringVar(value=self.settings.default_view.name)
        views = [m.name for m in ViewMode]
        
        opt_menu = ttk.OptionMenu(main_frame, self.view_var, self.settings.default_view.name, *views)
        opt_menu.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Apply & Save", command=self._save).pack(side=tk.RIGHT)
        
    def _save(self):
        self.settings.animation_speed = self.speed_var.get()
        self.settings.show_memory_on_thumbnails = self.mem_var.get()
        self.settings.show_borders = self.borders_var.get()
        self.settings.show_titles = self.titles_var.get()
        self.settings.default_view = ViewMode[self.view_var.get()]
        self.settings.flip3d_spacing = int(self.spacing_var.get())
        self.settings.flip3d_card_scale = self.scale_var.get()
        
        if self.callback:
            self.callback()
        self.destroy()

class ProcessCard:
    def __init__(self, canvas: tk.Canvas, process: ProcessInfo, x: float, y: float,
                 width: float = 200, height: float = 140, is_selected: bool = False,
                 show_memory: bool = True, show_borders: bool = True, show_titles: bool = True, 
                 click_callback=None):
        self.canvas = canvas
        self.process = process
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_selected = is_selected
        self.show_memory = show_memory
        self.show_borders = show_borders
        self.show_titles = show_titles
        self.click_callback = click_callback
        self.items = []
        self.tk_image = None 
        
    def _rotate_point(self, x, y, cx, cy, angle_rad):
        if angle_rad == 0:
            return x, y
        cos_val = math.cos(angle_rad)
        sin_val = math.sin(angle_rad)
        dx = x - cx
        dy = y - cy
        nx = cx + dx * cos_val - dy * sin_val
        ny = cy + dx * sin_val + dy * cos_val
        return nx, ny

    def draw(self, scale: float = 1.0, opacity: float = 1.0, rotation: float = 0, z_index: int = 0):
        w = self.width * scale
        h = self.height * scale
        
        # Logic for background colors
        if self.is_selected:
            bg_color = "#2d5a7b"
            border_color = "#4dd4e8"
            border_width = 3
        else:
            bg_color = "#1a1f3a"
            border_color = "#3a4070"
            border_width = 1
        
        x1, y1 = self.x - w/2, self.y - h/2
        x2, y2 = self.x + w/2, self.y + h/2
        radius = 12 * scale
        
        # Generate improved polygon points (manually tessellated rounded rect)
        # This fixes the visual glitch (spikes) by avoiding smooth=True on bad control points
        points = self._create_rounded_rect_points(x1, y1, x2, y2, radius)
        
        angle_rad = math.radians(rotation)
        if rotation != 0:
            rotated_points = []
            for i in range(0, len(points), 2):
                px, py = points[i], points[i+1]
                rx, ry = self._rotate_point(px, py, self.x, self.y, angle_rad)
                rotated_points.extend([rx, ry])
            points = rotated_points

        tag = f"card_{self.process.id}"
        
        # Draw Background/Frame only if enabled
        # NOTE: Removed smooth=True to prevent artifacts
        if self.show_borders:
            card_bg = self.canvas.create_polygon(
                points, fill=bg_color, outline=border_color, width=border_width, smooth=False,
                tags=tag
            )
            self.items.append(card_bg)
        
        # Draw Selection Glow (always draw if selected, but style differs if borders off)
        if self.is_selected:
            glow_width = 6 * scale
            if not self.show_borders:
                glow_width = 4 * scale
                
            glow = self.canvas.create_polygon(
                points, fill="", outline="#4dd4e8", width=glow_width, smooth=False,
                tags=tag
            )
            self.items.insert(0, glow)
        
        # Draw Image
        if self.process.image:
            try:
                # If borders are hidden, use full size, else with padding
                if self.show_borders:
                    img_w, img_h = int(w - 10*scale), int(h - 40*scale)
                else:
                    img_w, img_h = int(w), int(h)

                if img_w > 10 and img_h > 10:
                    pil_img = self.process.image.resize((img_w, img_h), Image.Resampling.BILINEAR)
                    
                    if abs(rotation) > 0.1:
                        pil_img = pil_img.rotate(rotation, expand=True, fillcolor=(0,0,0,0))
                    
                    self.tk_image = ImageTk.PhotoImage(pil_img)
                    img_item = self.canvas.create_image(self.x, self.y, image=self.tk_image, tags=tag)
                    self.items.append(img_item)
            except Exception:
                pass

        # Draw Fallback Icon if no image
        if not self.process.image:
            icon_size = int(36 * scale)
            icon_text = self.canvas.create_text(
                self.x, self.y - h/4, text=self.process.icon,
                font=("Segoe UI Emoji", icon_size), fill="white", tags=tag
            )
            self.items.append(icon_text)
        
        # Draw Title (Only if enabled)
        if self.show_titles:
            title_y = self.y + h/2 - 20*scale if self.process.image and self.show_borders else self.y + h/8
            
            if not self.show_borders and self.process.image:
                 title_y = self.y + h/2 - 15*scale

            if rotation != 0:
                 tx, ty = self._rotate_point(self.x, title_y, self.x, self.y, angle_rad)
                 text_x, text_y = tx, ty
            else:
                 text_x, text_y = self.x, title_y

            title_size = max(8, int(11 * scale))
            
            if not self.show_borders and self.process.image:
                 self.items.append(self.canvas.create_text(
                    text_x+1, text_y+1,
                    text=self._truncate_text(self.process.title, 25),
                    font=("Segoe UI", title_size, "bold"), fill="black", tags=tag
                ))

            title_text = self.canvas.create_text(
                text_x, text_y,
                text=self._truncate_text(self.process.title, 25),
                font=("Segoe UI", title_size, "bold"), fill="white", tags=tag
            )
            self.items.append(title_text)

        if self.show_memory and self.process.memory_mb > 0:
            # Adjust memory position
            if self.show_borders:
                mem_y = self.y - h/2 - 10*scale
            else:
                mem_y = self.y - h/2 + 10*scale

            if rotation != 0:
                mx, my = self._rotate_point(self.x, mem_y, self.x, self.y, angle_rad)
            else:
                mx, my = self.x, mem_y
            
            if not self.show_borders:
                 self.items.append(self.canvas.create_text(
                    mx+1, my+1, 
                    text=f"{self.process.memory_mb:.0f} MB",
                    font=("Arial", int(9*scale)), fill="black", tags=tag
                ))

            mem_text = self.canvas.create_text(
                mx, my, 
                text=f"{self.process.memory_mb:.0f} MB",
                font=("Arial", int(9*scale)), fill="#aaaaaa" if self.show_borders else "yellow", tags=tag
            )
            self.items.append(mem_text)

        # Ensure bindings are applied for right-click settings
        if self.click_callback:
            for item in self.items:
                self.canvas.tag_bind(item, "<Button-3>", lambda e: self.click_callback(e))
        
        return self.items
    
    def _create_rounded_rect_points(self, x1, y1, x2, y2, radius):
        # Manually tessellate rounded corners to avoid using smooth=True
        points = []
        steps = 8  # Number of segments per corner
        
        # Top-Right corner
        cx, cy = x2 - radius, y1 + radius
        for i in range(steps + 1):
            rad = math.radians(270 + (90 * i / steps))
            points.append(cx + radius * math.cos(rad))
            points.append(cy + radius * math.sin(rad))
            
        # Bottom-Right corner
        cx, cy = x2 - radius, y2 - radius
        for i in range(steps + 1):
            rad = math.radians(0 + (90 * i / steps))
            points.append(cx + radius * math.cos(rad))
            points.append(cy + radius * math.sin(rad))
            
        # Bottom-Left corner
        cx, cy = x1 + radius, y2 - radius
        for i in range(steps + 1):
            rad = math.radians(90 + (90 * i / steps))
            points.append(cx + radius * math.cos(rad))
            points.append(cy + radius * math.sin(rad))
            
        # Top-Left corner
        cx, cy = x1 + radius, y1 + radius
        for i in range(steps + 1):
            rad = math.radians(180 + (90 * i / steps))
            points.append(cx + radius * math.cos(rad))
            points.append(cy + radius * math.sin(rad))
            
        return points
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        return text if len(text) <= max_length else text[:max_length-3] + "..."
    
    def clear(self):
        self.tk_image = None
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

class WindowFlowManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Window Flow Manager")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        self._setup_transparent_window()
        
        self.current_index_float = 0.0
        self.target_index = 0
        self.animating = False
        self.visible = True
        self.settings_window = None
        
        self.processes: List[ProcessInfo] = []
        self.current_view = ViewMode.FLIP3D
        self.settings = AppSettings()
        self.cards: List[ProcessCard] = []
        
        self._load_config()
        self.current_view = self.settings.default_view

        self.monitor = get_process_monitor()
        self.monitor.subscribe(self._on_processes_updated_bg)
        
        self.canvas = tk.Canvas(
            self.root, width=self.screen_width, height=self.screen_height,
            bg='black', highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self._bind_events()
        self.monitor.start_auto_refresh(interval=3.0)
        
        self.mouse_hook = MouseHook(self._toggle_visibility)
        self.mouse_hook.start()
        
        self._animate_loop()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.settings.animation_speed = data.get('animation_speed', 0.1)
                    self.settings.default_view = ViewMode[data.get('default_view', 'FLIP3D')]
                    self.settings.flip3d_spacing = data.get('flip3d_spacing', 150)
                    self.settings.flip3d_card_scale = data.get('flip3d_card_scale', 1.0)
                    self.settings.show_memory_on_thumbnails = data.get('show_memory_on_thumbnails', True)
                    self.settings.show_borders = data.get('show_borders', True)
                    self.settings.show_titles = data.get('show_titles', True)
            except Exception as e:
                print(f"Error loading config: {e}")

    def _save_config(self):
        data = {
            'animation_speed': self.settings.animation_speed,
            'default_view': self.settings.default_view.name,
            'flip3d_spacing': self.settings.flip3d_spacing,
            'flip3d_card_scale': self.settings.flip3d_card_scale,
            'show_memory_on_thumbnails': self.settings.show_memory_on_thumbnails,
            'show_borders': self.settings.show_borders,
            'show_titles': self.settings.show_titles
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _setup_transparent_window(self):
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.attributes('-topmost', True)
        try:
            self.root.attributes('-transparentcolor', 'black')
            self.root.attributes('-alpha', 0.95)
        except: pass
        self.root.focus_force()
    
    def _bind_events(self):
        self.root.bind('<Left>', lambda e: self._nav_delta(-1))
        self.root.bind('<Right>', lambda e: self._nav_delta(1))
        self.root.bind('<Return>', lambda e: self._focus_selected())
        self.root.bind('<Escape>', lambda e: self._exit())
        self.root.bind('<Key-1>', lambda e: self._set_view(ViewMode.FLIP3D))
        self.root.bind('<Key-2>', lambda e: self._set_view(ViewMode.STAGE))
        self.root.bind('<Key-3>', lambda e: self._set_view(ViewMode.LIST))
        self.root.bind('<Key-k>', lambda e: self._kill_selected())
        self.root.bind('<Key-r>', lambda e: self._refresh())
        self.root.bind('<MouseWheel>', self._on_mouse_wheel)
        # Ensure global context menu works
        self.canvas.bind('<Button-3>', self._open_settings)

    def _toggle_visibility(self):
        if self.visible:
            self.root.after(0, self.root.withdraw)
            self.visible = False
        else:
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self._setup_transparent_window)
            self.visible = True

    def _open_settings(self, event):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.settings_window = SettingsDialog(self.root, self.settings, self._on_settings_changed)

    def _on_settings_changed(self):
        self.current_view = self.settings.default_view
        self._save_config()
        self._redraw()

    def _on_processes_updated_bg(self, processes):
        self.root.after(0, lambda: self._update_ui_data(processes))

    def _update_ui_data(self, processes):
        self.processes = processes
        if not processes:
            self.target_index = 0
            self.current_index_float = 0.0
        else:
            if self.target_index >= len(processes):
                self.target_index = len(processes) - 1
        
        if not self.animating:
            self._redraw()

    def _animate_loop(self):
        diff = self.target_index - self.current_index_float
        
        if abs(diff) > 0.001:
            self.animating = True
            speed = self.settings.animation_speed
            self.current_index_float += diff * speed
            self._redraw()
        else:
            self.current_index_float = float(self.target_index)
            if self.animating:
                self.animating = False
                self._redraw()
                
        self.root.after(16, self._animate_loop)

    def _redraw(self):
        if not self.visible: return
        try:
            self.canvas.delete("all")
            self.cards.clear()
            
            if not self.processes:
                self._draw_empty()
                return
            
            if self.current_view == ViewMode.FLIP3D:
                self._draw_flip3d()
            elif self.current_view == ViewMode.STAGE:
                self._draw_stage()
            else:
                self._draw_list()
                
            self._draw_overlay()
        except tk.TclError:
            pass

    def _draw_flip3d(self):
        cx, cy = self.screen_width / 2, self.screen_height / 2
        base_w, base_h = 340, 260
        spacing = self.settings.flip3d_spacing
        usr_scale = self.settings.flip3d_card_scale
        
        total = len(self.processes)
        draw_order = []
        
        for i in range(total):
            dist = i - self.current_index_float
            abs_dist = abs(dist)
            
            if abs_dist > 6: continue
            
            z_depth = -abs_dist
            draw_order.append((i, dist, z_depth))
            
        draw_order.sort(key=lambda x: x[2])
        
        for i, dist, z in draw_order:
            proc = self.processes[i]
            
            scale = max(0.5, 1.0 - (abs(dist) * 0.1)) * usr_scale
            
            x = cx + (dist * spacing * 0.8)
            y = cy + (abs(dist) * 20) 
            
            rot = -dist * 5
            
            is_sel = (int(round(self.current_index_float)) == i)
            
            card = ProcessCard(
                self.canvas, proc, x, y, base_w, base_h, 
                is_selected=is_sel, 
                show_memory=self.settings.show_memory_on_thumbnails,
                show_borders=self.settings.show_borders,
                show_titles=self.settings.show_titles,
                click_callback=self._open_settings
            )
            card.draw(scale=scale, rotation=rot)
            self.cards.append(card)

    def _draw_stage(self):
        cw, ch = 220, 160
        sel_idx = int(round(self.current_index_float))
        
        y_off = 100
        for i, proc in enumerate(self.processes):
            if i == sel_idx: continue
            if y_off + ch > self.screen_height: break
            
            card = ProcessCard(self.canvas, proc, 150, y_off, cw, ch, False, 
                               show_memory=self.settings.show_memory_on_thumbnails,
                               show_borders=self.settings.show_borders,
                               show_titles=self.settings.show_titles,
                               click_callback=self._open_settings)
            card.draw(scale=0.7)
            self.cards.append(card)
            y_off += ch + 10
            
        if 0 <= sel_idx < len(self.processes):
            main = self.processes[sel_idx]
            card = ProcessCard(self.canvas, main, self.screen_width/2 + 120, self.screen_height/2, 
                               640, 480, True, 
                               show_memory=self.settings.show_memory_on_thumbnails,
                               show_borders=self.settings.show_borders,
                               show_titles=self.settings.show_titles,
                               click_callback=self._open_settings)
            card.draw(scale=1.0)
            self.cards.append(card)

    def _draw_list(self):
        cw, ch = 240, 180
        cols = max(1, int((self.screen_width - 100) / (cw + 20)))
        
        sel_idx = int(round(self.current_index_float))
        
        for i, proc in enumerate(self.processes):
            c = i % cols
            r = i // cols
            
            x = 100 + cw/2 + c * (cw+20)
            y = 100 + ch/2 + r * (ch+20)
            
            if y > self.screen_height - 50: continue
            
            card = ProcessCard(self.canvas, proc, x, y, cw, ch, (i == sel_idx),
                               show_memory=self.settings.show_memory_on_thumbnails,
                               show_borders=self.settings.show_borders,
                               show_titles=self.settings.show_titles,
                               click_callback=self._open_settings)
            card.draw(scale=1.0)
            self.cards.append(card)

    def _draw_empty(self):
        self.canvas.create_text(self.screen_width/2, self.screen_height/2, text="No windows found", fill="white", font=("Arial", 24))

    def _draw_overlay(self):
        # CLEANED UP: Removed overlay text (View name and counters)
        pass

    def _nav_delta(self, delta):
        if not self.processes: return
        new_idx = self.target_index + delta
        
        if new_idx < 0: new_idx = len(self.processes) - 1
        if new_idx >= len(self.processes): new_idx = 0
        
        self.target_index = new_idx

    def _focus_selected(self):
        if not self.processes: return
        idx = int(round(self.current_index_float))
        proc = self.processes[idx]
        try:
            import win32gui, win32con
            win32gui.ShowWindow(proc.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(proc.hwnd)
            self.root.withdraw()
            sys.exit(0)
        except:
            pass

    def _kill_selected(self):
        if not self.processes: return
        idx = int(round(self.current_index_float))
        pid = self.processes[idx].pid
        self.monitor.kill_process(pid)

    def _refresh(self):
        self.monitor.refresh_processes()

    def _set_view(self, mode):
        self.current_view = mode
        self._redraw()

    def _on_mouse_wheel(self, event):
        if event.delta < 0:
            self._nav_delta(1)
        else:
            self._nav_delta(-1)

    def _exit(self):
        self.monitor.stop_auto_refresh()
        self.mouse_hook.stop()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WindowFlowManager().run()