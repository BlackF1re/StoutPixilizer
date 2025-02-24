import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, PhotoImage
from PIL import Image, ImageTk

def resource_path(relative_path):
    """ Возвращает путь к файлу (учитывает упаковку в .exe) """
    if hasattr(sys, '_MEIPASS'):  #если из .exe
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

class StoutPixilizer:
    def __init__(self, root):
        self.root = root
        self.root.title("*New - Stout Pixilizer")

        #logo setup
        icon_path = "assets/logo.png"
        icon_image = icon = Image.open(icon_path).resize((64, 64), Image.LANCZOS) 
        icon_photo = ImageTk.PhotoImage(icon_image)

        root.iconphoto(False, icon_photo)


        self.cell_size = 10
        self.cols = 96
        self.rows = 16
        self.scale_factor = 1.5
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.history = []  #История изменений
        self.history_index = -1  #Индекс текущего состояния в истории
        self.file_path = None
        self.unsaved_changes = False

        button_frame = tk.Frame(root)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        self.icons = {
            "save": ImageTk.PhotoImage(Image.open(resource_path("assets/save_image.png")).resize((24, 24))),
            "open": ImageTk.PhotoImage(Image.open(resource_path("assets/open_image.png")).resize((24, 24))),
            "clear": ImageTk.PhotoImage(Image.open(resource_path("assets/clear_canvas.png")).resize((24, 24))),
            "close": ImageTk.PhotoImage(Image.open(resource_path("assets/close_file.png")).resize((24, 24))),
            "center": ImageTk.PhotoImage(Image.open(resource_path("assets/center_grid.png")).resize((24, 24))),
            "ruler": ImageTk.PhotoImage(Image.open(resource_path("assets/toggle_ruler.png")).resize((24, 24))),
        }

        save_button = tk.Button(button_frame, image=self.icons["save"], command=self.save_image, width=32, height=32, compound=tk.CENTER)
        save_button.pack(side=tk.LEFT, padx=2, pady=5)

        open_button = tk.Button(button_frame, image=self.icons["open"], command=self.open_image, width=32, height=32, compound=tk.CENTER)
        open_button.pack(side=tk.LEFT, padx=2, pady=5)

        clear_button = tk.Button(button_frame, image=self.icons["clear"], command=self.clear_canvas, width=32, height=32, compound=tk.CENTER)
        clear_button.pack(side=tk.LEFT, padx=2, pady=5)

        close_button = tk.Button(button_frame, image=self.icons["close"], command=self.close_file, width=32, height=32, compound=tk.CENTER)
        close_button.pack(side=tk.LEFT, padx=2, pady=5)

        center_button = tk.Button(button_frame, image=self.icons["center"], command=self.center_grid, width=32, height=32, compound=tk.CENTER)
        center_button.pack(side=tk.LEFT, padx=2, pady=5)

        ruler_button = tk.Button(button_frame, image=self.icons["ruler"], command=self.toggle_ruler, width=32, height=32, compound=tk.CENTER)
        ruler_button.pack(side=tk.LEFT, padx=2, pady=5)

        #Холст, привязки и отступы
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

        #Бинды
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

        self.show_ruler = False

        self.draw_grid()
        self.update_canvas_size()
        self.root.geometry("1920x480")
    
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
                return  #Отмена
            if result:  #Да
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
                return  #Отмена
            if result:  #Да
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
            #имя файла, если изменений нет
            title = f"{self.file_path.split('/')[-1]} - Stout Pixilizer"
        else:
            title = "Stout Pixilizer"
        self.root.title(title)
    
    def center_grid(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        grid_width = self.cols * self.cell_size * self.scale_factor
        grid_height = self.rows * self.cell_size * self.scale_factor

        # калькуляция масштаба для вписывания сетки в холст
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
