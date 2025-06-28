import cv2
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import json
import os
from datetime import timedelta


class VideoAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("视频标注工具_v2") # Version update

        # Initialize parameters
        self.video_path = ""
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.current_frame = 0
        self.playing = False
        self.base_delay = 25
        self.playback_speed = 1.0

        # Annotation parameters
        self.annotations = []
        self.selected_annotation = None # Will store the item ID from Treeview
        self.annotation_mode = "rectangle"
        self.temp_rect_canvas_id = None # Renamed from self.temp_rect

        # Game Type and Role variables
        self.game_type_var = tk.StringVar(value="CS2")
        self.role_var = tk.StringVar(value="警")


        # Display parameters
        self.canvas_width = 1280
        self.canvas_height = 720
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Annotation save status
        self.annotations_saved = True
        self.last_save_path = None

        # Create main layout
        self.create_main_layout()
        self.create_context_menu()

        # Bind close window event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_game_type_changed(self, *args):
        """Callback when game_type_var changes."""
        self.update_role_ui()

    def create_main_layout(self):
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        top_container = tk.Frame(main_container)
        top_container.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(top_container, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        left_panel.pack_propagate(False)

        file_frame = tk.Frame(left_panel)
        file_frame.pack(fill=tk.X, pady=5)
        ttk.Button(file_frame, text="打开视频", command=self.open_video).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="加载标注", command=self.load_annotations).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="保存标注", command=self.save_annotations).pack(side=tk.LEFT, padx=2)

        info_frame = tk.LabelFrame(left_panel, text="视频信息")
        info_frame.pack(fill=tk.X, pady=5)

        tk.Label(info_frame, text="游戏视频名称:").pack(anchor=tk.W, padx=5)
        self.video_name_label = tk.Label(info_frame, text="未加载", wraplength=280)
        self.video_name_label.pack(anchor=tk.W, padx=5)

        game_frame = tk.Frame(info_frame)
        game_frame.pack(fill=tk.X, pady=2)
        tk.Label(game_frame, text="游戏类型:").pack(side=tk.LEFT, padx=5)
        self.game_type_combobox = ttk.Combobox(game_frame, textvariable=self.game_type_var,
                                               values=["CS2", "APEX"], width=15)
        self.game_type_combobox.pack(side=tk.LEFT)
        self.game_type_var.trace_add('write', self.on_game_type_changed)

        lang_frame = tk.Frame(info_frame)
        lang_frame.pack(fill=tk.X, pady=2)
        tk.Label(lang_frame, text="语言:").pack(side=tk.LEFT, padx=5)
        self.language_var = tk.StringVar(value="zh_CN")
        ttk.Combobox(lang_frame, textvariable=self.language_var, values=["en_US", "zh_CN"],
                     state="readonly", width=10).pack(side=tk.LEFT)

        prop_frame = tk.LabelFrame(left_panel, text="标注属性")
        prop_frame.pack(fill=tk.X, pady=5)

        role_ui_frame = tk.Frame(prop_frame)
        role_ui_frame.pack(fill=tk.X, pady=2)
        tk.Label(role_ui_frame, text="角色:").pack(side=tk.LEFT, padx=5)
        self.role_input_frame = tk.Frame(role_ui_frame)
        self.role_input_frame.pack(side=tk.LEFT)
        self.update_role_ui()

        kill_frame = tk.Frame(prop_frame)
        kill_frame.pack(fill=tk.X, pady=2)
        tk.Label(kill_frame, text="击杀时刻(帧):").pack(side=tk.LEFT, padx=5)
        self.kill_frame_var = tk.StringVar(value="NA")
        ttk.Entry(kill_frame, textvariable=self.kill_frame_var, width=10).pack(side=tk.LEFT)

        right_panel = tk.Frame(top_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.canvas = tk.Canvas(right_panel, width=self.canvas_width, height=self.canvas_height, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        bottom_container = tk.Frame(main_container)
        bottom_container.pack(fill=tk.X, pady=5)

        control_frame = tk.Frame(bottom_container)
        control_frame.pack(fill=tk.X)

        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(fill=tk.X)

        self.btn_play = ttk.Button(btn_frame, text="▶ 播放", command=self.toggle_play, width=8)
        self.btn_play.pack(side=tk.LEFT, padx=2)
        self.btn_prev = ttk.Button(btn_frame, text="◀ 前一帧 (Q)", command=self.prev_frame, width=12)
        self.btn_prev.pack(side=tk.LEFT, padx=2)
        self.btn_next = ttk.Button(btn_frame, text="后一帧 (W) ▶", command=self.next_frame, width=12)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        tk.Label(btn_frame, text="倍速:").pack(side=tk.LEFT, padx=2)
        self.speed_var = tk.StringVar()
        self.speed_combobox = ttk.Combobox(btn_frame, textvariable=self.speed_var,
                                           values=["0.5x", "1x", "2x", "4x", "8x", "16x", "32x", "64x"], width=5)
        self.speed_combobox.current(1)
        self.speed_combobox.pack(side=tk.LEFT, padx=2)
        self.speed_combobox.bind("<<ComboboxSelected>>", self.update_playback_speed)

        time_frame = tk.Frame(control_frame)
        time_frame.pack(fill=tk.X, pady=2)
        self.lbl_time = ttk.Label(time_frame, text="帧号: 0 | 时间: 00:00:00.000")
        self.lbl_time.pack(side=tk.LEFT)
        self.ent_time = ttk.Entry(time_frame, width=8)
        self.ent_time.pack(side=tk.RIGHT, padx=2)
        ttk.Button(time_frame, text="时间跳转", command=self.jump_to_time, width=8).pack(side=tk.RIGHT, padx=2)
        tk.Label(time_frame, text="时间格式(m:s):").pack(side=tk.RIGHT, padx=2)
        self.ent_frame = ttk.Entry(time_frame, width=8)
        self.ent_frame.pack(side=tk.RIGHT, padx=2)
        ttk.Button(time_frame, text="帧号跳转", command=self.jump_to_frame, width=8).pack(side=tk.RIGHT, padx=2)

        self.slider = ttk.Scale(control_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                command=self.update_frame_from_slider)
        self.slider.pack(fill=tk.X, pady=2)

        list_frame = tk.LabelFrame(bottom_container, text="标注列表操作") # Changed to LabelFrame
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0)) # Added padding top

        # Treeview for annotations
        tree_container = tk.Frame(list_frame) # Container for tree and scrollbar
        tree_container.pack(fill=tk.BOTH, expand=True)

        columns = ("游戏视频名称", "游戏类型", "标注时刻", "标注帧数", "角色名", "坐标点位", "标注面积", "击杀时刻(帧)",
                   "击杀时刻(秒)", "语言")
        self.annotation_tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=5) # Adjusted height
        for col in columns:
            self.annotation_tree.heading(col, text=col)
            self.annotation_tree.column(col, width=80, anchor=tk.CENTER)
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.annotation_tree.yview)
        self.annotation_tree.configure(yscrollcommand=tree_scroll.set)
        self.annotation_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons for annotation list operations
        list_op_button_frame = tk.Frame(list_frame)
        list_op_button_frame.pack(fill=tk.X, pady=2)

        ttk.Button(list_op_button_frame, text="删除选中", command=self.delete_selected_annotation_from_tree).pack(side=tk.LEFT, padx=2)
        # *** NEW FEATURE: Delete All Annotations button ***
        ttk.Button(list_op_button_frame, text="删除全部标注", command=self.delete_all_annotations).pack(side=tk.LEFT, padx=2)


        self.canvas.bind("<Button-1>", self.start_annotation)
        self.canvas.bind("<B1-Motion>", self.draw_temp_rect)
        self.canvas.bind("<ButtonRelease-1>", self.end_annotation)
        self.annotation_tree.bind("<<TreeviewSelect>>", self.select_annotation_from_tree)
        self.root.bind('<q>', lambda e: self.prev_frame())
        self.root.bind('<w>', lambda e: self.next_frame())
        self.root.bind('<space>', lambda e: self.toggle_play())

    def update_role_ui(self):
        for widget in self.role_input_frame.winfo_children():
            widget.destroy()
        current_game_type = self.game_type_var.get()
        if current_game_type == "CS2":
            self.role_specific_widget = ttk.Combobox(self.role_input_frame, textvariable=self.role_var,
                                                     values=["警", "匪"], width=10)
            self.role_specific_widget.pack(side=tk.LEFT)
            if not self.role_var.get() or self.role_var.get() not in ["警", "匪"]:
                self.role_var.set("警")
        else:
            self.role_specific_widget = ttk.Entry(self.role_input_frame, textvariable=self.role_var, width=12)
            self.role_specific_widget.pack(side=tk.LEFT)

    def prev_frame(self):
        if self.cap and self.current_frame > 0:
            self.current_frame -= 1
            self.slider.set(self.current_frame)
            self.display_current_frame()

    def next_frame(self):
        if self.cap and self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.slider.set(self.current_frame)
            self.display_current_frame()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="编辑选中标注", command=self.edit_selected_annotation)
        self.context_menu.add_command(label="删除选中标注", command=self.delete_selected_annotation_from_tree)
        self.annotation_tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        item_id = self.annotation_tree.identify_row(event.y)
        if item_id:
            self.annotation_tree.selection_set(item_id)
            self.selected_annotation = item_id
            self.context_menu.post(event.x_root, event.y_root)

    def update_playback_speed(self, event=None):
        speed_map = {"0.5x": 0.5, "1x": 1.0, "2x": 2.0, "4x": 4.0,
                     "8x": 8.0, "16x": 16.0, "32x": 32.0, "64x": 64.0}
        selected_speed_str = self.speed_var.get()
        self.playback_speed = speed_map.get(selected_speed_str, 1.0)

    def open_video(self):
        path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4 *.avi *.mov")])
        if not path: return
        self.video_path = path
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件")
            self.video_path = ""
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0: self.fps = 25.0
        self.current_frame = 0
        self.slider.config(to=self.total_frames - 1 if self.total_frames > 0 else 0)
        self.slider.set(0)
        self.video_name_label.config(text=os.path.basename(path))
        self.playing = False
        self.btn_play.config(text="▶ 播放")
        self.annotations = []
        self.update_annotation_list_display()
        self.try_load_auto_annotations()
        self.display_current_frame()

    def try_load_auto_annotations(self):
        if not self.video_path: return
        base_path = os.path.splitext(self.video_path)[0]
        json_path = f"{base_path}_annotations.json"
        if os.path.exists(json_path):
            if messagebox.askyesno("发现标注文件", "检测到关联标注文件，是否加载？"):
                self.load_annotations(json_path)

    def get_current_time_seconds(self):
        return self.current_frame / self.fps if self.fps > 0 else 0

    def format_time(self, seconds):
        td = timedelta(seconds=seconds)
        h, rem = divmod(td.seconds, 3600)
        m, s_val = divmod(rem, 60) # Renamed s to s_val
        ms = td.microseconds // 1000
        return f"{h:02d}:{m:02d}:{s_val:02d}.{ms:03d}"

    def update_time_display(self):
        time_str = self.format_time(self.get_current_time_seconds())
        self.lbl_time.config(text=f"帧号: {self.current_frame} | 时间: {time_str}")

    def calculate_area(self, coords):
        return abs((coords["x2"] - coords["x1"]) * (coords["y2"] - coords["y1"]))

    def parse_kill_time_to_frame(self, kill_time_str):
        if not kill_time_str or str(kill_time_str).lower() == "na": return None
        try: return int(float(kill_time_str))
        except ValueError: return None

    def parse_kill_time_to_seconds(self, kill_time_str):
        frame = self.parse_kill_time_to_frame(kill_time_str)
        if frame is None or not self.fps or self.fps == 0: return None
        return round(frame / self.fps, 3)

    def start_annotation(self, event):
        if not self.cap or not self.cap.isOpened(): return
        self.start_x_orig = (event.x - self.offset_x) / self.scale
        self.start_y_orig = (event.y - self.offset_y) / self.scale
        if self.temp_rect_canvas_id: self.canvas.delete(self.temp_rect_canvas_id) # Clear previous one if any
        self.temp_rect_canvas_id = None

    def draw_temp_rect(self, event):
        if not hasattr(self, 'start_x_orig'): return
        if self.temp_rect_canvas_id: self.canvas.delete(self.temp_rect_canvas_id)

        end_x_orig = (event.x - self.offset_x) / self.scale
        end_y_orig = (event.y - self.offset_y) / self.scale

        x1_canvas = self.start_x_orig * self.scale + self.offset_x
        y1_canvas = self.start_y_orig * self.scale + self.offset_y
        x2_canvas = end_x_orig * self.scale + self.offset_x
        y2_canvas = end_y_orig * self.scale + self.offset_y

        self.temp_rect_canvas_id = self.canvas.create_rectangle(
            x1_canvas, y1_canvas, x2_canvas, y2_canvas, outline="cyan", tags="temp_rect_drawing_tag")

    def end_annotation(self, event):
        if not hasattr(self, 'start_x_orig') or not self.cap or not self.cap.isOpened():
            if self.temp_rect_canvas_id: self.canvas.delete(self.temp_rect_canvas_id)
            self.temp_rect_canvas_id = None
            if hasattr(self, 'start_x_orig'): delattr(self, 'start_x_orig')
            if hasattr(self, 'start_y_orig'): delattr(self, 'start_y_orig')
            return

        end_x_orig = (event.x - self.offset_x) / self.scale
        end_y_orig = (event.y - self.offset_y) / self.scale

        frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        coords_x1 = max(0, min(int(min(self.start_x_orig, end_x_orig)), frame_w))
        coords_y1 = max(0, min(int(min(self.start_y_orig, end_y_orig)), frame_h))
        coords_x2 = max(0, min(int(max(self.start_x_orig, end_x_orig)), frame_w))
        coords_y2 = max(0, min(int(max(self.start_y_orig, end_y_orig)), frame_h))

        if abs(coords_x2 - coords_x1) > 5 and abs(coords_y2 - coords_y1) > 5:
            kill_time_str = self.kill_frame_var.get()
            kill_frame_val = self.parse_kill_time_to_frame(kill_time_str)
            kill_seconds_val = self.parse_kill_time_to_seconds(kill_time_str)
            annotation = {
                "video_name": os.path.basename(self.video_path) if self.video_path else "N/A",
                "game_type": self.game_type_var.get(),
                "time": self.get_current_time_seconds(),
                "frame": self.current_frame,
                "role": self.role_var.get(),
                "coords": {"x1": coords_x1, "y1": coords_y1, "x2": coords_x2, "y2": coords_y2},
                "area": self.calculate_area({"x1": coords_x1, "y1": coords_y1, "x2": coords_x2, "y2": coords_y2}),
                "kill_time": kill_frame_val if kill_frame_val is not None else "NA",
                "kill": kill_seconds_val if kill_seconds_val is not None else "",
                "language": self.language_var.get()
            }
            self.add_annotation_to_list(annotation)

        if self.temp_rect_canvas_id: self.canvas.delete(self.temp_rect_canvas_id)
        self.temp_rect_canvas_id = None
        delattr(self, 'start_x_orig'); delattr(self, 'start_y_orig')

    def add_annotation_to_list(self, annotation):
        self.annotations.append(annotation)
        self.annotations_saved = False
        self.update_annotation_list_display()
        self.draw_annotations_on_canvas()

    def find_annotation_index_by_tree_item_id(self, item_id):
        if not item_id: return -1
        try:
            item_values = self.annotation_tree.item(item_id, "values")
            target_frame = int(item_values[3])
            target_coords_str = item_values[5]
            for i, ann in enumerate(self.annotations):
                ann_coords_str = f"({ann['coords']['x1']},{ann['coords']['y1']})-({ann['coords']['x2']},{ann['coords']['y2']})"
                if ann["frame"] == target_frame and ann_coords_str == target_coords_str:
                    return i
        except (IndexError, ValueError): return -1
        return -1

    def edit_selected_annotation(self):
        if not self.selected_annotation:
            messagebox.showwarning("警告", "请先在列表中选择一个标注进行编辑。")
            return
        original_annotation_index = self.find_annotation_index_by_tree_item_id(self.selected_annotation)
        if original_annotation_index == -1:
            messagebox.showerror("错误", "无法找到原始标注数据进行编辑。")
            return
        original = self.annotations[original_annotation_index]
        edit_win = tk.Toplevel(self.root); edit_win.title("编辑标注"); edit_win.geometry("350x180")
        edit_win.transient(self.root); edit_win.grab_set()
        tk.Label(edit_win, text="角色:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        role_var_edit = tk.StringVar(value=original.get("role", ""))
        role_edit_frame = tk.Frame(edit_win); role_edit_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        annotation_game_type = original.get("game_type", self.game_type_var.get())
        if annotation_game_type == "CS2":
            ttk.Combobox(role_edit_frame, textvariable=role_var_edit, values=["警", "匪"], width=15).pack(side=tk.LEFT)
        else:
            ttk.Entry(role_edit_frame, textvariable=role_var_edit, width=17).pack(side=tk.LEFT)
        tk.Label(edit_win, text="击杀时刻(帧):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        kill_time_var_edit = tk.StringVar(value=str(original.get("kill_time", "NA")))
        ttk.Entry(edit_win, textvariable=kill_time_var_edit, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        def save_changes_edit():
            original["role"] = role_var_edit.get()
            kf_edit = self.parse_kill_time_to_frame(kill_time_var_edit.get())
            ks_edit = self.parse_kill_time_to_seconds(kill_time_var_edit.get())
            original["kill_time"] = kf_edit if kf_edit is not None else "NA"
            original["kill"] = ks_edit if ks_edit is not None else ""
            self.annotations_saved = False
            self.update_annotation_list_display(); self.draw_annotations_on_canvas()
            edit_win.destroy()
        ttk.Button(edit_win, text="保存修改", command=save_changes_edit).grid(row=2, column=0, columnspan=2, pady=10)
        edit_win.grid_columnconfigure(1, weight=1)

    def delete_selected_annotation_from_tree(self):
        if not self.selected_annotation:
            messagebox.showwarning("警告", "请先在列表中选择一个标注进行删除。")
            return
        original_annotation_index = self.find_annotation_index_by_tree_item_id(self.selected_annotation)
        if original_annotation_index != -1:
            del self.annotations[original_annotation_index]
            self.annotation_tree.delete(self.selected_annotation)
            self.selected_annotation = None
            self.annotations_saved = False
            self.draw_annotations_on_canvas()
        else:
            messagebox.showerror("错误", "无法在数据中找到选中的标注进行删除。")

    # *** NEW METHOD: Delete All Annotations ***
    def delete_all_annotations(self):
        if not self.annotations:
            messagebox.showinfo("提示", "当前没有标注可供删除。")
            return

        if messagebox.askyesno("确认删除", "您确定要删除所有标注吗？此操作无法撤销。"):
            self.annotations.clear()
            # Clear the Treeview
            for item in self.annotation_tree.get_children():
                self.annotation_tree.delete(item)
            
            self.selected_annotation = None # Clear selection state
            self.annotations_saved = False # Mark as unsaved
            self.draw_annotations_on_canvas() # Redraw canvas to remove annotations
            messagebox.showinfo("操作完成", "所有标注已成功删除。")


    def update_annotation_list_display(self):
        for item in self.annotation_tree.get_children(): self.annotation_tree.delete(item)
        for ann in self.annotations:
            self.annotation_tree.insert("", "end", values=(
                ann.get("video_name", "N/A"), ann.get("game_type", "N/A"),
                self.format_time(ann.get("time", 0)), ann.get("frame", 0),
                ann.get("role", ""),
                f"({ann['coords']['x1']},{ann['coords']['y1']})-({ann['coords']['x2']},{ann['coords']['y2']})",
                ann.get("area", 0), ann.get("kill_time", "NA"),
                ann.get("kill", ""), ann.get("language", "N/A")
            ))

    def save_annotations(self):
        if not self.annotations: messagebox.showwarning("警告", "没有需要保存的标注"); return
        if not self.video_path: messagebox.showerror("错误", "请先打开一个视频文件。"); return
        base_p = os.path.splitext(self.video_path)[0]
        def_fn = f"{os.path.basename(base_p)}_annotations.json"
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=def_fn, filetypes=[("JSON文件", "*.json")])
        if path:
            fw = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap and self.cap.isOpened() else 0
            fh = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap and self.cap.isOpened() else 0
            data = {"video_info": {"fps": self.fps, "width": fw, "height": fh,
                                   "name": os.path.basename(self.video_path), "game_type": self.game_type_var.get()},
                    "annotations": self.annotations}
            try:
                with open(path, "w", encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("保存成功", "标注文件已保存")
                self.annotations_saved = True; self.last_save_path = path
            except Exception as e: messagebox.showerror("保存失败", f"保存标注文件时发生错误: {e}")

    def load_annotations(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")])
            if not path: return
        try:
            with open(path, "r", encoding='utf-8') as f: data = json.load(f)
            vid_info, ann_loaded = data.get("video_info", {}), data.get("annotations", [])
            if self.cap and self.cap.isOpened():
                curr_w, load_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), vid_info.get("width", 0)
                if load_w != 0 and curr_w != load_w:
                    if not messagebox.askyesno("警告", "标注文件的视频分辨率与当前视频不一致，继续加载吗？"): return
            loaded_fps = vid_info.get("fps", self.fps if self.fps > 0 else 25.0)
            for ann in ann_loaded:
                kt_val, k_val = ann.get("kill_time"), ann.get("kill")
                try:
                    if kt_val is not None and str(kt_val).lower() not in ["", "na"]:
                        ann["kill_time"] = int(float(kt_val))
                        if (k_val is None or str(k_val) == "") and loaded_fps > 0: ann["kill"] = round(ann["kill_time"] / loaded_fps, 3)
                        elif k_val is not None and str(k_val) != "": ann["kill"] = round(float(k_val),3)
                        else: ann["kill"] = ""
                    elif k_val is not None and str(k_val) != "" and loaded_fps > 0:
                        ann["kill"] = round(float(k_val),3); ann["kill_time"] = int(round(ann["kill"] * loaded_fps))
                    else: ann["kill_time"], ann["kill"] = "NA", ""
                except ValueError: ann["kill_time"], ann["kill"] = "NA", ""
            self.annotations = ann_loaded
            if vid_info.get("game_type"): self.game_type_var.set(vid_info.get("game_type"))
            self.update_annotation_list_display(); messagebox.showinfo("加载成功", "标注文件已加载")
            self.draw_annotations_on_canvas(); self.annotations_saved = True; self.last_save_path = path
        except Exception as e: messagebox.showerror("错误", f"加载标注文件失败: {str(e)}")

    def jump_to_frame(self):
        if not self.cap or not self.cap.isOpened(): return
        try:
            f_str = self.ent_frame.get();
            if not f_str: return
            frame = int(f_str)
            if 0 <= frame < self.total_frames:
                self.current_frame, self.slider.set(frame), self.display_current_frame()
            else: messagebox.showwarning("警告", f"帧号需在 0 和 {self.total_frames -1}之间。")
        except ValueError: messagebox.showwarning("警告", "请输入有效的帧号。")

    def jump_to_time(self):
        if not self.cap or not self.cap.isOpened() or self.fps == 0: return
        try:
            t_str = self.ent_time.get();
            if not t_str: return
            m, s_val = map(float, t_str.split(':')) # Renamed s to s_val
            frame = int((m * 60 + s_val) * self.fps)
            if 0 <= frame < self.total_frames:
                self.current_frame, self.slider.set(frame), self.display_current_frame()
            else: messagebox.showwarning("警告", "时间超出视频范围。")
        except ValueError: messagebox.showwarning("警告", "时间格式 (分:秒) 无效。")

    def toggle_play(self):
        if not self.cap or not self.cap.isOpened(): return
        self.playing = not self.playing
        self.btn_play.config(text="⏸ 暂停" if self.playing else "▶ 播放")
        if self.playing: self.play_video_loop()

    @property
    def actual_delay(self):
        delay = int(self.base_delay / self.playback_speed) if self.playback_speed > 0 else self.base_delay
        return max(1, delay)

    def play_video_loop(self):
        if self.playing and self.cap and self.cap.isOpened() and self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.slider.set(self.current_frame)
            self.display_current_frame()
            self.root.after(self.actual_delay, self.play_video_loop)
        else:
            self.playing = False; self.btn_play.config(text="▶ 播放")
            if self.cap and self.cap.isOpened() and self.current_frame >= self.total_frames -1 :
                 self.current_frame = max(0, self.total_frames -1)
                 self.slider.set(self.current_frame); self.display_current_frame()

    def update_frame_from_slider(self, slider_val):
        if self.cap and self.cap.isOpened():
            frame_num = int(float(slider_val))
            if self.current_frame != frame_num:
                self.current_frame = frame_num; self.display_current_frame()

    def display_current_frame(self):
        if not self.cap or not self.cap.isOpened(): return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame_bgr = self.cap.read()
        if ret:
            self.update_time_display(); self.show_cv_frame_on_canvas(frame_bgr)
        elif self.playing:
            self.playing = False; self.btn_play.config(text="▶ 播放")

    def show_cv_frame_on_canvas(self, cv_frame_bgr):
        frame_rgb = cv2.cvtColor(cv_frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]
        if w == 0 or h == 0: return
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        canvas_w = canvas_w if canvas_w > 1 else self.canvas_width
        canvas_h = canvas_h if canvas_h > 1 else self.canvas_height
        self.scale = min(canvas_w / w, canvas_h / h)
        new_w, new_h = int(w * self.scale), int(h * self.scale)
        self.offset_x, self.offset_y = (canvas_w - new_w) // 2, (canvas_h - new_h) // 2
        img_pil = Image.fromarray(frame_rgb).resize((new_w, new_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(image=img_pil)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_img)
        self.draw_annotations_on_canvas()

    def draw_annotations_on_canvas(self):
        self.canvas.delete("annotation_drawing_tag")
        for ann in self.annotations:
            if ann["frame"] == self.current_frame:
                color = "red" if ann.get("role") == "匪" else "blue"
                if ann.get("game_type") == "APEX": color = "purple"
                x1_d = ann["coords"]["x1"] * self.scale + self.offset_x
                y1_d = ann["coords"]["y1"] * self.scale + self.offset_y
                x2_d = ann["coords"]["x2"] * self.scale + self.offset_x
                y2_d = ann["coords"]["y2"] * self.scale + self.offset_y
                self.canvas.create_rectangle(x1_d, y1_d, x2_d, y2_d, outline=color, width=2, tags="annotation_drawing_tag")
                self.canvas.create_text(x1_d + 5, y1_d + 5, text=str(ann.get("role", "")), fill=color,
                                        anchor=tk.NW, font=("Arial", 12, "bold"), tags="annotation_drawing_tag")

    def select_annotation_from_tree(self, event):
        selection = self.annotation_tree.selection()
        if selection:
            self.selected_annotation = selection[0]
            try:
                item_values = self.annotation_tree.item(self.selected_annotation, "values")
                frame_to_jump = int(item_values[3])
                if self.cap and self.cap.isOpened() and 0 <= frame_to_jump < self.total_frames:
                    self.current_frame, self.slider.set(frame_to_jump), self.display_current_frame()
            except (ValueError, IndexError): pass

    def on_closing(self):
        if not self.annotations_saved and self.annotations:
            ans = messagebox.askyesnocancel("退出提示", "标注信息尚未保存，是否保存？")
            if ans is None: return
            elif ans:
                if self.last_save_path and self.cap and self.cap.isOpened():
                    try:
                        fw, fh = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        vn, gt = os.path.basename(self.video_path) if self.video_path else "N/A", self.game_type_var.get()
                        data = {"video_info": {"fps": self.fps, "width": fw, "height": fh, "name": vn, "game_type": gt},
                                "annotations": self.annotations}
                        with open(self.last_save_path, "w", encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)
                        self.annotations_saved = True
                    except Exception as e:
                        if messagebox.askyesno("自动保存失败", f"自动保存失败: {e}\n是否尝试手动保存？"):
                            self.save_annotations()
                            if not self.annotations_saved: return
                        else: return
                else:
                    self.save_annotations()
                    if not self.annotations_saved: return
        if self.cap: self.cap.release()
        self.root.destroy()

    def __del__(self):
        if hasattr(self, 'cap') and self.cap: self.cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x960")
    app = VideoAnnotator(root)
    root.mainloop()