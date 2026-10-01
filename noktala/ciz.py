import tkinter as tk
from tkinter import filedialog, messagebox, Scale
import numpy as np
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class CurvedSurfaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eğri Yüzey ve Kalınlık Gösterimi")
        self.root.geometry("1200x900")
        
        # Ana panel - sol ve sağ olarak ayıralım
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol panel (kontrol ve bilgi)
        left_frame = tk.Frame(main_frame, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_frame.pack_propagate(False)
        
        # Sağ panel (grafik)
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Kontrol paneli (sol üst)
        control_frame = tk.LabelFrame(left_frame, text="Kontroller", font=('Arial', 10, 'bold'))
        control_frame.pack(fill=tk.X, pady=5)
        
        # Dosya yükleme butonu
        self.load_btn = tk.Button(control_frame, text="📂 XYZ Dosyasını Yükle", command=self.load_file)
        self.load_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # Z ölçek slider'ı
        tk.Label(control_frame, text="Z Ölçek:").pack(pady=(10,0))
        self.z_scale = Scale(control_frame, from_=0.1, to=50.0, resolution=0.1, 
                             orient=tk.HORIZONTAL, length=250, command=self.update_z_scale)
        self.z_scale.set(1.0)
        self.z_scale.pack(pady=5, padx=5)
        
        # Z değerini gösteren etiket
        self.z_label = tk.Label(control_frame, text="1.00x", font=('Arial', 10, 'bold'))
        self.z_label.pack(pady=2)
        
        # 360 Derece Döndürme Slider'ı
        tk.Label(control_frame, text="360° Döndürme:", font=('Arial', 10, 'bold')).pack(pady=(15,0))
        
        # Yatay döndürme (Azimuth)
        frame_azim = tk.Frame(control_frame)
        frame_azim.pack(fill=tk.X, pady=2)
        tk.Label(frame_azim, text="Yatay:", width=8, anchor='w').pack(side=tk.LEFT)
        self.azimuth_slider = Scale(frame_azim, from_=0, to=360, resolution=1, 
                                   orient=tk.HORIZONTAL, length=180, 
                                   command=self.update_rotation)
        self.azimuth_slider.set(45)
        self.azimuth_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.azimuth_label = tk.Label(frame_azim, text="45°", width=6)
        self.azimuth_label.pack(side=tk.LEFT, padx=5)
        
        # Dikey döndürme (Elevation)
        frame_elev = tk.Frame(control_frame)
        frame_elev.pack(fill=tk.X, pady=2)
        tk.Label(frame_elev, text="Dikey:", width=8, anchor='w').pack(side=tk.LEFT)
        self.elevation_slider = Scale(frame_elev, from_=-90, to=90, resolution=1, 
                                     orient=tk.HORIZONTAL, length=180, 
                                     command=self.update_rotation)
        self.elevation_slider.set(30)
        self.elevation_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.elevation_label = tk.Label(frame_elev, text="30°", width=6)
        self.elevation_label.pack(side=tk.LEFT, padx=5)
        
        # Görünüm butonları
        tk.Label(control_frame, text="Hızlı Görünüm:", font=('Arial', 10, 'bold')).pack(pady=(10,5))
        
        view_btn_frame = tk.Frame(control_frame)
        view_btn_frame.pack(pady=5)
        
        self.btn_top = tk.Button(view_btn_frame, text="Üst (Z)", command=self.view_top, 
                                 bg='lightblue', width=10)
        self.btn_top.pack(side=tk.LEFT, padx=2)
        
        self.btn_front = tk.Button(view_btn_frame, text="Ön (X)", command=self.view_front, 
                                   bg='lightgreen', width=10)
        self.btn_front.pack(side=tk.LEFT, padx=2)
        
        self.btn_side = tk.Button(view_btn_frame, text="Yan (Y)", command=self.view_side, 
                                  bg='lightcoral', width=10)
        self.btn_side.pack(side=tk.LEFT, padx=2)
        
        self.btn_reset = tk.Button(view_btn_frame, text="Reset", command=self.view_reset, 
                                   bg='lightyellow', width=10)
        self.btn_reset.pack(side=tk.LEFT, padx=2)
        
        # Bilgi paneli (sol orta)
        info_frame = tk.LabelFrame(left_frame, text="Koordinat Bilgileri", font=('Arial', 10, 'bold'))
        info_frame.pack(fill=tk.X, pady=5)
        
        # Eksen limitleri
        self.limits_text = tk.Text(info_frame, height=8, width=35, font=('Courier', 9))
        self.limits_text.pack(padx=5, pady=5, fill=tk.X)
        self.limits_text.insert('1.0', "Eksen Limitleri:\n")
        self.limits_text.insert('end', "X: bekleniyor...\n")
        self.limits_text.insert('end', "Y: bekleniyor...\n")
        self.limits_text.insert('end', "Z: bekleniyor...\n")
        self.limits_text.config(state='disabled')
        
        # Matplotlib figürü ve canvas (sağ panel)
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Fare ile döndürme için bağlantılar (tıklama olmadan sadece sürükleme)
        self.drag_start = None
        self.azim_init = None
        self.elev_init = None
        self.canvas.mpl_connect('button_press_event', self.on_mouse_down)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_up)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        # Verileri sakla
        self.points = None
        self.points_original = None
        self.z_scale_value = 1.0
        self.default_elev = 30
        self.default_azim = 45
        self.thickness = 1.0
        self.x_grid = None
        self.y_grid = None
        self.z_grid = None
        self.updating_sliders = False  # Slider güncellemesi sırasında döngüyü önle
        
    def load_file(self):
        """xyz.txt dosyasını yükler ve yüzeyi oluşturur."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
        
        try:
            points = []
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.replace(',', ' ')
                    values = line.strip().split()
                    if len(values) >= 3:
                        try:
                            x = float(values[0])
                            y = float(values[1])
                            z = float(values[2])
                            points.append([x, y, z])
                        except ValueError:
                            continue
            
            if len(points) < 4:
                messagebox.showerror("Hata", f"Yetersiz nokta sayısı: {len(points)} (en az 4 gerekli).")
                return
            
            self.points_original = np.array(points)
            print(f"{len(self.points_original)} nokta okundu.")
            
            # Limitleri güncelle
            self.update_limits()
            
            # Z ölçeğini uygula
            self.apply_z_scale()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya okunamadı: {e}")
    
    def update_limits(self):
        """Eksen limitlerini güncelle."""
        if self.points_original is None:
            return
        
        x_min, x_max = self.points_original[:, 0].min(), self.points_original[:, 0].max()
        y_min, y_max = self.points_original[:, 1].min(), self.points_original[:, 1].max()
        z_min, z_max = self.points_original[:, 2].min(), self.points_original[:, 2].max()
        
        self.limits_text.config(state='normal')
        self.limits_text.delete('1.0', tk.END)
        self.limits_text.insert('1.0', "Eksen Limitleri (orijinal):\n")
        self.limits_text.insert('end', f"X min: {x_min:.4f}  max: {x_max:.4f}\n")
        self.limits_text.insert('end', f"Y min: {y_min:.4f}  max: {y_max:.4f}\n")
        self.limits_text.insert('end', f"Z min: {z_min:.4f}  max: {z_max:.4f}\n")
        self.limits_text.insert('end', f"Nokta Sayısı: {len(self.points_original)}")
        self.limits_text.config(state='disabled')
    
    def apply_z_scale(self):
        """Z ölçeğini uygula ve yüzeyi yeniden çiz."""
        if self.points_original is None:
            return
        
        self.points = self.points_original.copy()
        self.points[:, 2] = self.points_original[:, 2] * self.z_scale_value
        
        self.create_curved_surface()
    
    def update_z_scale(self, value):
        """Slider değeri değiştiğinde çağrılır."""
        self.z_scale_value = float(value)
        self.z_label.config(text=f"{self.z_scale_value:.2f}x")
        self.apply_z_scale()
    
    def update_rotation(self, value):
        """Döndürme slider'ları değiştiğinde çağrılır."""
        if self.updating_sliders:
            return
        
        try:
            azim = float(self.azimuth_slider.get())
            elev = float(self.elevation_slider.get())
            
            # Etiketleri güncelle
            self.azimuth_label.config(text=f"{azim:.0f}°")
            self.elevation_label.config(text=f"{elev:.0f}°")
            
            # Görünümü güncelle
            self.ax.view_init(elev=elev, azim=azim)
            self.canvas.draw_idle()
        except:
            pass
    
    def create_curved_surface(self):
        """Noktalardan eğri bir yüzey oluşturur ve 1mm kalınlık ekler."""
        if self.points is None or len(self.points) < 4:
            return
        
        # Delaunay triangülasyonu ile yüzey oluştur
        tri = Delaunay(self.points[:, :2])
        
        # Yüzeyi düzgün hale getirmek için enterpolasyon
        xi = np.linspace(self.points[:, 0].min(), self.points[:, 0].max(), 100)
        yi = np.linspace(self.points[:, 1].min(), self.points[:, 1].max(), 100)
        self.x_grid, self.y_grid = np.meshgrid(xi, yi)
        
        # Enterpolasyon fonksiyonu
        interp = LinearNDInterpolator(tri, self.points[:, 2])
        zi = interp(self.x_grid, self.y_grid)
        self.z_grid = np.nan_to_num(zi)
        
        # Kalınlık (1 mm)
        thickness = self.thickness
        
        # Alt ve üst yüzeyler
        zi_top = self.z_grid + thickness / 2
        zi_bottom = self.z_grid - thickness / 2
        
        # Grafiği temizle
        self.ax.clear()
        
        # Üst yüzeyi çiz
        surf_top = self.ax.plot_surface(self.x_grid, self.y_grid, zi_top, alpha=0.7, cmap='viridis')
        # Alt yüzeyi çiz
        surf_bottom = self.ax.plot_surface(self.x_grid, self.y_grid, zi_bottom, alpha=0.3, cmap='plasma')
        
        # Kenarları bağla
        for i in range(self.x_grid.shape[0]):
            self.ax.plot(self.x_grid[i, :], self.y_grid[i, :], zi_top[i, :], color='gray', linewidth=0.5, alpha=0.3)
            self.ax.plot(self.x_grid[i, :], self.y_grid[i, :], zi_bottom[i, :], color='gray', linewidth=0.5, alpha=0.3)
        for j in range(self.x_grid.shape[1]):
            self.ax.plot(self.x_grid[:, j], self.y_grid[:, j], zi_top[:, j], color='gray', linewidth=0.5, alpha=0.3)
            self.ax.plot(self.x_grid[:, j], self.y_grid[:, j], zi_bottom[:, j], color='gray', linewidth=0.5, alpha=0.3)
        
        # Yan kenarlar
        x_min_idx = 0
        self.ax.plot(self.x_grid[x_min_idx, :], self.y_grid[x_min_idx, :], zi_top[x_min_idx, :], color='blue', linewidth=2)
        self.ax.plot(self.x_grid[x_min_idx, :], self.y_grid[x_min_idx, :], zi_bottom[x_min_idx, :], color='blue', linewidth=2)
        x_max_idx = -1
        self.ax.plot(self.x_grid[x_max_idx, :], self.y_grid[x_max_idx, :], zi_top[x_max_idx, :], color='blue', linewidth=2)
        self.ax.plot(self.x_grid[x_max_idx, :], self.y_grid[x_max_idx, :], zi_bottom[x_max_idx, :], color='blue', linewidth=2)
        y_min_idx = 0
        self.ax.plot(self.x_grid[:, y_min_idx], self.y_grid[:, y_min_idx], zi_top[:, y_min_idx], color='red', linewidth=2)
        self.ax.plot(self.x_grid[:, y_min_idx], self.y_grid[:, y_min_idx], zi_bottom[:, y_min_idx], color='red', linewidth=2)
        y_max_idx = -1
        self.ax.plot(self.x_grid[:, y_max_idx], self.y_grid[:, y_max_idx], zi_top[:, y_max_idx], color='red', linewidth=2)
        self.ax.plot(self.x_grid[:, y_max_idx], self.y_grid[:, y_max_idx], zi_bottom[:, y_max_idx], color='red', linewidth=2)
        
        # Orijinal noktaları göster - KÜÇÜK boyutta
        self.ax.scatter(self.points[:, 0], self.points[:, 1], self.points[:, 2], 
                       color='black', s=10, alpha=0.6, label='Orijinal Noktalar')
        
        # Eksen etiketleri
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title(f'Eğri Yüzey (Kalınlık: {thickness} mm, Z Ölçek: {self.z_scale_value:.2f}x)')
        
        # Eşit eksen oranı
        max_range = np.array([self.x_grid.max()-self.x_grid.min(), 
                             self.y_grid.max()-self.y_grid.min(), 
                             zi_top.max()-zi_top.min()]).max() / 2.0
        mid_x = (self.x_grid.max()+self.x_grid.min()) * 0.5
        mid_y = (self.y_grid.max()+self.y_grid.min()) * 0.5
        mid_z = (zi_top.max()+zi_top.min()) * 0.5
        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Slider değerlerini kullanarak görünümü ayarla
        current_azim = float(self.azimuth_slider.get())
        current_elev = float(self.elevation_slider.get())
        self.ax.view_init(elev=current_elev, azim=current_azim)
        
        # Canvas'ı güncelle
        self.canvas.draw()
    
    def view_top(self):
        """Z ekseninden (üstten) bakış."""
        self.updating_sliders = True
        self.azimuth_slider.set(0)
        self.elevation_slider.set(90)
        self.azimuth_label.config(text="0°")
        self.elevation_label.config(text="90°")
        self.updating_sliders = False
        self.ax.view_init(elev=90, azim=0)
        self.canvas.draw_idle()
    
    def view_front(self):
        """X ekseninden (önden) bakış."""
        self.updating_sliders = True
        self.azimuth_slider.set(0)
        self.elevation_slider.set(0)
        self.azimuth_label.config(text="0°")
        self.elevation_label.config(text="0°")
        self.updating_sliders = False
        self.ax.view_init(elev=0, azim=0)
        self.canvas.draw_idle()
    
    def view_side(self):
        """Y ekseninden (yandan) bakış."""
        self.updating_sliders = True
        self.azimuth_slider.set(90)
        self.elevation_slider.set(0)
        self.azimuth_label.config(text="90°")
        self.elevation_label.config(text="0°")
        self.updating_sliders = False
        self.ax.view_init(elev=0, azim=90)
        self.canvas.draw_idle()
    
    def view_reset(self):
        """Varsayılan görünüme dön."""
        self.updating_sliders = True
        self.azimuth_slider.set(45)
        self.elevation_slider.set(30)
        self.azimuth_label.config(text="45°")
        self.elevation_label.config(text="30°")
        self.updating_sliders = False
        self.ax.view_init(elev=30, azim=45)
        self.canvas.draw_idle()
    
    def on_mouse_down(self, event):
        """Fare tuşuna basıldığında başlangıç açılarını sakla."""
        if event.inaxes == self.ax:
            self.drag_start = (event.x, event.y)
            self.azim_init = self.ax.azim
            self.elev_init = self.ax.elev
    
    def on_mouse_up(self, event):
        """Fare tuşu bırakıldığında."""
        self.drag_start = None
    
    def on_mouse_move(self, event):
        """Fare hareket ettikçe görünümü döndür ve slider'ları güncelle."""
        if self.drag_start is not None and event.inaxes == self.ax:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            
            sensitivity = 0.5
            new_azim = self.azim_init + dx * sensitivity
            new_elev = self.elev_init - dy * sensitivity
            new_elev = np.clip(new_elev, -90, 90)
            
            # Slider'ları güncelle (döngüyü önlemek için)
            self.updating_sliders = True
            self.azimuth_slider.set(new_azim % 360)
            self.elevation_slider.set(new_elev)
            self.azimuth_label.config(text=f"{new_azim % 360:.0f}°")
            self.elevation_label.config(text=f"{new_elev:.0f}°")
            self.updating_sliders = False
            
            # Görünümü güncelle
            self.ax.view_init(elev=new_elev, azim=new_azim)
            self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk()
    app = CurvedSurfaceApp(root)
    root.mainloop()
