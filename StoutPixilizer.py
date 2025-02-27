import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Константы
CELL_SIZE = 10
COLS = 96
ROWS = 16
INITIAL_SCALE_FACTOR = 1.5
ICON_SIZE = (64, 64)
BUTTON_ICON_SIZE = (24, 24)
WINDOW_GEOMETRY = "1920x480"

def resource_path(relative_path):
    """ Возвращает путь к файлу (учитывает упаковку в .exe) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class StoutPixilizer:
    def __init__(self, root):
        self.root = root
        self.root.title("*New - Stout Pixilizer")

        #logo setup
        icon_path = resource_path("assets/logo.png")
        icon_image = Image.open(icon_path).resize(ICON_SIZE, Image.LANCZOS)
        icon_photo = ImageTk.PhotoImage(icon_image)
        root.iconphoto(False, icon_photo)

        self.cell_size = CELL_SIZE
        self.cols = COLS
        self.rows = ROWS
        self.scale_factor = INITIAL_SCALE_FACTOR
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.history = []
        self.history_index = -1
        self.file_path = None
        self.unsaved_changes = False

        self.setup_ui()
        self.bind_events()

        self.show_ruler = False

        self.draw_grid()
        self.update_canvas_size()
        self.root.geometry(WINDOW_GEOMETRY)

    def setup_ui(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        self.icons = {
            "save": ImageTk.PhotoImage(Image.open(resource_path("assets/save_image.png")).resize(BUTTON_ICON_SIZE)),
            "open": ImageTk.PhotoImage(Image.open(resource_path("assets/open_image.png")).resize(BUTTON_ICON_SIZE)),
            "clear": ImageTk.PhotoImage(Image.open(resource_path("assets/clear_canvas.png")).resize(BUTTON_ICON_SIZE)),
            "close": ImageTk.PhotoImage(Image.open(resource_path("assets/close_file.png")).resize(BUTTON_ICON_SIZE)),
            "center": ImageTk.PhotoImage(Image.open(resource_path("assets/center_grid.png")).resize(BUTTON_ICON_SIZE)),
            "ruler": ImageTk.PhotoImage(Image.open(resource_path("assets/toggle_ruler.png")).resize(BUTTON_ICON_SIZE)),
        }

        self.create_button(button_frame, "save", self.save_image, "Save")
        self.create_button(button_frame, "open", self.open_image, "Open")
        self.create_button(button_frame, "clear", self.clear_canvas, "Clear")
        self.create_button(button_frame, "close", self.close_file, "Close")
        self.create_button(button_frame, "center", self.center_grid, "Center")
        self.create_button(button_frame, "ruler", self.toggle_ruler, "Toggle Ruler")

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(self.canvas_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def create_button(self, frame, icon_key, command, tooltip_text):
        button = tk.Button(frame, image=self.icons[icon_key], command=command, width=32, height=32, compound=tk.CENTER)
        button.pack(side=tk.LEFT, padx=2, pady=5)
        ToolTip(button, tooltip_text)

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.paint_pixel)
        self.canvas.bind("<Button-3>", self.erase_pixel)
        self.canvas.bind("<B1-Motion>", self.paint_pixel)
        self.canvas.bind("<B3-Motion>", self.erase_pixel)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<ButtonPress-2>", self.start_drag)
        self.canvas.bind("<B2-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-2>", self.stop_drag)
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-y>", self.redo)
        self.root.bind("<Control-s>", self.save_image)

    def draw_grid(self):
        self.canvas.delete("all")
        for y in range(self.rows):
            for x in range(self.cols):
                x1 = x * self.cell_size * self.scale_factor + self.offset_x
                y1 = y * self.cell_size * self.scale_factor + self.offset_y
                x2 = x1 + self.cell_size * self.scale_factor
                y2 = y1 + self.cell_size * self.scale_factor
                color = 'white' if self.grid[y][x] else 'black'
                outline_color = 'red' if self.show_ruler and (x == self.cols // 2 or y == self.rows // 2 or (self.cols % 2 == 0 and x == self.cols // 2 - 1) or (self.rows % 2 == 0 and y == self.rows // 2 - 1)) else 'white'
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline_color)
        self.update_canvas_size()

    def update_canvas_size(self):
        width = self.cols * self.cell_size * self.scale_factor
        height = self.rows * self.cell_size * self.scale_factor
        self.canvas.config(width=width, height=height)

    def paint_pixel(self, event):
        x = int((event.x - self.offset_x) // (self.cell_size * self.scale_factor))
        y = int((event.y - self.offset_y) // (self.cell_size * self.scale_factor))
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[y][x] = 1
            self.save_state()
            self.draw_grid()

    def erase_pixel(self, event):
        x = int((event.x - self.offset_x) // (self.cell_size * self.scale_factor))
        y = int((event.y - self.offset_y) // (self.cell_size * self.scale_factor))
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[y][x] = 0
            self.save_state()
            self.draw_grid()

    def save_state(self):
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append([row[:] for row in self.grid])
        self.history_index += 1
        self.unsaved_changes = True
        self.update_window_title()

    def undo(self, event=None):
        if self.history_index > 0:
            self.history_index -= 1
            self.grid = [row[:] for row in self.history[self.history_index]]
            self.draw_grid()

    def redo(self, event=None):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.grid = [row[:] for row in self.history[self.history_index]]
            self.draw_grid()

    def save_image(self, event=None):
        if not self.file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".bmp",
                filetypes=[("Bitmap Image", "*.bmp"),
                         ("PNG Image", "*.png"),
                         ("JPEG Image", "*.jpg"),
                         ("GIF Image", "*.gif"),
                         ("JPEG Image", "*.jpeg")]
            )
            if not file_path:
                return
            self.file_path = file_path
        try:
            img = Image.new("1", (self.cols, self.rows), 0)
            pixels = img.load()
            for y in range(self.rows):
                for x in range(self.cols):
                    pixels[x, y] = 255 if self.grid[y][x] else 0
            img.save(self.file_path)
            self.unsaved_changes = False
            self.update_window_title()
            messagebox.showinfo("Сохранено", "Изображение успешно сохранено!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def open_image(self):
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "Сохранить изменения?", "У вас есть несохраненные изменения. Сохранить их?"
            )
            if result is None:
                return
            if result:
                self.save_image()

        file_path = filedialog.askopenfilename(
            filetypes=[("Bitmap Image", "*.bmp"),
                     ("PNG Image", "*.png"),
                     ("JPEG Image", "*.jpg"),
                     ("GIF Image", "*.gif"),
                     ("JPEG Image", "*.jpeg")]
        )
        if not file_path:
            return
        try:
            img = Image.open(file_path).convert("1")
            if img.size != (self.cols, self.rows):
                messagebox.showerror("Ошибка", "Файл должен быть размером 96x16 пикселей")
                return
            pixels = img.load()
            self.file_path = file_path
            self.history.clear()
            self.history_index = -1
            self.grid = [[1 if pixels[x, y] == 255 else 0 for x in range(self.cols)] for y in range(self.rows)]
            self.save_state()
            self.draw_grid()
            self.update_window_title()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def close_file(self):
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "Сохранить изменения?", "У вас есть несохраненные изменения. Сохранить их?"
            )
            if result is None:
                return
            if result:
                self.save_image()

        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.history.clear()
        self.history_index = -1
        self.file_path = None
        self.unsaved_changes = False
        self.draw_grid()
        self.update_window_title()

    def zoom(self, event):
        old_scale = self.scale_factor
        if event.delta > 0 and self.scale_factor < 5:
            self.scale_factor += 0.5
        elif event.delta < 0 and self.scale_factor > 0.5:
            self.scale_factor -= 0.5

        mouse_x = event.x
        mouse_y = event.y

        scale_ratio = self.scale_factor / old_scale
        self.offset_x = mouse_x - (mouse_x - self.offset_x) * scale_ratio
        self.offset_y = mouse_y - (mouse_y - self.offset_y) * scale_ratio

        self.draw_grid()

    def start_drag(self, event):
        self.dragging = True
        self.drag_start_x = event.x - self.offset_x
        self.drag_start_y = event.y - self.offset_y

    def drag(self, event):
        if self.dragging:
            self.offset_x = event.x - self.drag_start_x
            self.offset_y = event.y - self.drag_start_y
            self.draw_grid()

    def stop_drag(self, event):
        self.dragging = False

    def clear_canvas(self):
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.save_state()
        self.draw_grid()

    def update_window_title(self):
        if self.unsaved_changes:
            #*имя файла, если файл существует и есть несохраненные изменения
            title = f"*{self.file_path.split('/')[-1]} - Stout Pixilizer" if self.file_path else "*New - Stout Pixilizer"
        elif self.file_path:
            title = f"{self.file_path.split('/')[-1]} - Stout Pixilizer"
        else:
            title = "Stout Pixilizer"
        self.root.title(title)

    def center_grid(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        grid_width = self.cols * self.cell_size * self.scale_factor
        grid_height = self.rows * self.cell_size * self.scale_factor

        scale_x = canvas_width / grid_width
        scale_y = canvas_height / grid_height
        scale = min(scale_x, scale_y)

        self.scale_factor = scale
        self.offset_x = (canvas_width - grid_width * self.scale_factor) / 2
        self.offset_y = (canvas_height - grid_height * self.scale_factor) / 2

        self.draw_grid()

    def toggle_ruler(self):
        self.show_ruler = not self.show_ruler
        self.draw_grid()

if __name__ == "__main__":
    root = tk.Tk()
    editor = StoutPixilizer(root)
    root.state("zoomed")
    root.mainloop()
