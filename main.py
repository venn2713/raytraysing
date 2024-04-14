import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np
from PIL import Image, ImageTk  # For displaying images in tkinter
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import OpenGL.GL.shaders as shaders


def normalize(vector):
    return vector / np.linalg.norm(vector)


def reflected(vector, axis):
    return vector - 2 * np.dot(vector, axis) * axis


def sphere_intersect(center, radius, ray_origin, ray_direction):
    b = 2 * np.dot(ray_direction, ray_origin - center)
    c = np.linalg.norm(ray_origin - center) ** 2 - radius ** 2
    delta = b ** 2 - 4 * c
    if delta > 0:
        t1 = (-b + np.sqrt(delta)) / 2
        t2 = (-b - np.sqrt(delta)) / 2
        if t1 > 0 and t2 > 0:
            return min(t1, t2)
    return None


def nearest_intersected_object(objects, ray_origin, ray_direction):
    distances = [sphere_intersect(obj['центр'], obj['радиус'], ray_origin, ray_direction) for obj in objects]
    nearest_object = None
    min_distance = np.inf
    for index, distance in enumerate(distances):
        if distance and distance < min_distance:
            min_distance = distance
            nearest_object = objects[index]
    return nearest_object, min_distance


def object_exists(parent, name):
    return any(obj['имя'] == name for obj in parent.objects)


class ObjectEditor:
    def __init__(self, parent, title, obj=None):
        self.parent = parent
        self.obj = obj if obj else self.default_object
        self.idx_obj = parent.objects.index(self.obj) if obj else None
        self.editor = tk.Toplevel(parent)
        self.editor.title(title)
        self.editor.geometry("290x205")
        self.entries = {}
        self.create_fields()

    @property
    def default_object(self):
        # Значения по умолчанию для нового объекта
        return {
            'имя': 'Объект',
            'центр': np.array([0.0, 0.0, 0.0]),
            'радиус': 1.0,
            'фон. свет': np.array([1.0, 1.0, 1.0]),
            'расс. свет': np.array([1.0, 1.0, 1.0]),
            'зерк. свет': np.array([1.0, 1.0, 1.0]),
            'блеск': 50,
            'отражение': 0.5
        }

    def create_fields(self):
        row = 0
        for key, value in self.obj.items():
            if key in ['центр', 'фон. свет', 'расс. свет', 'зерк. свет']:
                tk.Label(self.editor, text=f"{key}:").grid(row=row, column=0, sticky='e', padx=5)
                coords = ['x', 'y', 'z'] if key == 'центр' else ['r', 'g', 'b']
                for idx, coord in enumerate(coords):
                    tk.Label(self.editor, text=f"{coord}:").grid(row=row, column=2 * idx + 1, sticky='w', padx=2)
                    entry_var = tk.StringVar(value=str(value[idx]))
                    self.entries[f"{key}_{coord}"] = tk.Entry(self.editor, textvariable=entry_var, width=5)
                    self.entries[f"{key}_{coord}"].grid(row=row, column=2 * idx + 2, sticky='w', padx=2)
                row += 1
            elif isinstance(value, (int, float, str)):
                tk.Label(self.editor, text=f"{key}:").grid(row=row, column=0, sticky='e', padx=5)
                entry_var = tk.StringVar(value=str(value))
                self.entries[key] = tk.Entry(self.editor, textvariable=entry_var, width=15)
                self.entries[key].grid(row=row, column=1, columnspan=5, sticky='w')
                row += 1

        button_frame = tk.Frame(self.editor)
        button_frame.grid(row=row, column=0, columnspan=6, pady=5)

        tk.Button(button_frame, text="Сохранить", command=lambda: self.save(), bg='green', fg='white').pack(
            side=tk.LEFT,
            padx=10,
            fill='x',
            expand=True
        )
        if self.idx_obj is not None:
            tk.Button(button_frame, text="Удалить", command=lambda: self.delete(), bg='red', fg='white').pack(
                side=tk.LEFT,
                padx=10,
                fill='x',
                expand=True
            )
            tk.Button(button_frame, text="Отмена", command=lambda: self.cancel()).pack(
                side=tk.LEFT,
                padx=10,
                fill='x',
                expand=True
            )
        else:
            tk.Button(button_frame, text="Отмена", command=lambda: self.cancel(), bg='red', fg='white').pack(
                side=tk.LEFT,
                padx=10,
                fill='x',
                expand=True
            )

    def save(self):
        try:
            new_name = self.entries['имя'].get()
            if self.idx_obj is None and object_exists(self.parent, new_name):
                messagebox.showerror("Ошибка", f"Объект с именем '{new_name}' уже существует.")
                return
            # Проверяем, изменилось ли имя объекта
            name_changed = new_name != self.obj['имя']
            self.obj['имя'] = new_name
            for key, entry in self.entries.items():
                if '_' in key:
                    base_key, coord = key.rsplit('_', 1)
                    # Определяем, является ли параметр вектором 'center', 'ambient', 'diffuse', 'specular'
                    if base_key in ['центр']:
                        idx = ['x', 'y', 'z'].index(coord)
                        self.obj[base_key][idx] = float(entry.get())
                    elif base_key in ['фон. свет', 'расс. свет', 'зерк. свет']:
                        idx = ['r', 'g', 'b'].index(coord)
                        self.obj[base_key][idx] = float(entry.get())
                elif key in ['радиус', 'блеск', 'отражение']:
                    self.obj[key] = float(entry.get())
            if self.idx_obj:
                self.parent.objects[self.idx_obj] = self.obj
                if name_changed:
                    self.parent.update_menu()  # Обновляем меню только если было изменение имени
            else:
                self.parent.objects.append(self.obj)
                self.parent.update_menu()
            self.editor.destroy()
        except ValueError as e:
            messagebox.showerror("Неверный ввод", f"Пожалуйста, введите корректные значения")

    def cancel(self):
        self.editor.destroy()

    def delete(self):
        if messagebox.askyesno("Подтвердите удаление", "Вы уверены, что хотите удалить этот объект?"):
            self.parent.objects.remove(self.obj)
            self.parent.update_menu()
            self.editor.destroy()


class RayTracerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Ray Tracer')

        # Define these before calling create_widgets
        self.width = 800
        self.height = 600
        self.geometry(f'{self.width}x{self.height}')
        self.max_depth = 3
        self.camera = np.array([0, 0, 1])
        self.ratio = float(self.width) / self.height
        self.screen = (-1, 1 / self.ratio, 1, -1 / self.ratio)  # left, top, right, bottom

        self.objects = [
            {
                'имя': "красный шар",
                'центр': np.array([-0.2, 0, -1]),
                'радиус': 0.7,
                'фон. свет': np.array([0.1, 0, 0]),
                'расс. свет': np.array([0.7, 0, 0]),
                'зерк. свет': np.array([1, 1, 1]),
                'блеск': 100,
                'отражение': 0.5
            },
            {
                'имя': "фиолетовый шар",
                'центр': np.array([0.1, -0.3, 0]),
                'радиус': 0.1,
                'фон. свет': np.array([0.1, 0, 0.1]),
                'расс. свет': np.array([0.7, 0, 0.7]),
                'зерк. свет': np.array([1, 1, 1]),
                'блеск': 100,
                'отражение': 0.5
            },
            {
                'имя': "зеленый шар",
                'центр': np.array([-0.3, 0, 0]),
                'радиус': 0.15,
                'фон. свет': np.array([0, 0.1, 0]),
                'расс. свет': np.array([0, 0.6, 0]),
                'зерк. свет': np.array([1, 1, 1]),
                'блеск': 100,
                'отражение': 0.5
            }
        ]
        self.light = {
            'позиция': np.array([5, 5, 5]),
            'фон. свет': np.array([1, 1, 1]),
            'расс. свет': np.array([1, 1, 1]),
            'зерк. свет': np.array([1, 1, 1])
        }

        self.create_widgets()
        self.create_menu()
    def create_menu(self):
        self.menu_bar = tk.Menu(self)  # Создание главного меню

        # Создание выпадающего меню для объектов
        self.objects_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Объекты", menu=self.objects_menu)

        self.update_menu()

        self.config(menu=self.menu_bar)  # Привязка главного меню к окну приложения

    def object_menu(self, obj):
        ObjectEditor(self, f"Редактирование: {obj['имя']}", obj)

    def add_new_object(self):
        ObjectEditor(self, "Добавление нового объекта")

    def update_menu(self):
        # Обновление меню объектов после удаления или добавления объекта
        self.objects_menu.delete(0, 'end')
        for obj in self.objects:
            self.objects_menu.add_command(label=obj['имя'], command=lambda x=obj: self.object_menu(x))
        self.objects_menu.add_separator()
        self.objects_menu.add_command(label="Добавить...", command=self.add_new_object)

    def create_widgets(self):
        # Создание фреймов для упорядочивания элементов интерфейса
        control_frame = tk.Frame(self)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        progress_frame = tk.Frame(control_frame)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        self.render_btn = tk.Button(control_frame, text='Render', command=self.render_scene)
        self.render_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        self.canvas = tk.Canvas(self, width=self.width, height=self.height, bg='black')
        self.canvas.pack(expand=True, fill=tk.BOTH)

    def render_scene(self):
        self.progress['value'] = 0  # Обнуляем прогресс перед началом рендеринга
        self.progress['maximum'] = self.height  # Максимальное значение равно количеству строк изображения

        image = np.zeros((self.height, self.width, 3))
        for i, y in enumerate(np.linspace(self.screen[1], self.screen[3], self.height)):
            for j, x in enumerate(np.linspace(self.screen[0], self.screen[2], self.width)):
                pixel = np.array([x, y, 0])
                origin = self.camera
                direction = normalize(pixel - origin)
                color = np.zeros(3)
                reflection = 1
                for k in range(self.max_depth):
                    nearest_object, min_distance = nearest_intersected_object(self.objects, origin, direction)
                    if nearest_object is None:
                        break
                    intersection = origin + min_distance * direction
                    normal_to_surface = normalize(intersection - nearest_object['центр'])
                    shifted_point = intersection + 1e-5 * normal_to_surface
                    intersection_to_light = normalize(self.light['позиция'] - shifted_point)
                    _, min_distance = nearest_intersected_object(self.objects, shifted_point, intersection_to_light)
                    intersection_to_light_distance = np.linalg.norm(self.light['позиция'] - intersection)
                    is_shadowed = min_distance < intersection_to_light_distance
                    if is_shadowed:
                        break
                    illumination = np.zeros(3)
                    illumination += nearest_object['фон. свет'] * self.light['фон. свет']
                    illumination += nearest_object['расс. свет'] * self.light['расс. свет'] * np.dot(intersection_to_light,
                                                                                               normal_to_surface)
                    intersection_to_camera = normalize(self.camera - intersection)
                    H = normalize(intersection_to_light + intersection_to_camera)
                    illumination += nearest_object['зерк. свет'] * self.light['зерк. свет'] * np.dot(normal_to_surface,
                                                                                                 H) ** (
                                                nearest_object['блеск'] / 4)
                    color += reflection * illumination
                    reflection *= nearest_object['отражение']
                    origin = shifted_point
                    direction = reflected(direction, normal_to_surface)
                image[i, j] = np.clip(color, 0, 1)
            self.progress['value'] += 1  # Обновляем прогресс после обработки каждой строки
            self.update()  # Обновляем GUI, чтобы изменения отображались во время выполнения

        self.display_image(image)

    def display_image(self, image):
        image = (image * 255).astype(np.uint8)
        photo = ImageTk.PhotoImage(image=Image.fromarray(image))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo  # Keep a reference!


app = RayTracerApp()
app.mainloop()
