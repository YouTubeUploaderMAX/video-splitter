#!/usr/bin/env python3
# Windows-specific version with path handling
import os
import sys
import subprocess
import threading
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QRadioButton, QButtonGroup, 
                              QSpinBox, QLabel, QTextEdit, QFileDialog, QProgressBar,
                              QFrame, QSizePolicy, QComboBox, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette, QColor


class WorkerThread(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)
    error = Signal(str)
    segment_progress = Signal(int)

    def __init__(self, input_path, output_dir, segment_duration, mode, resolution, scale_crop):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.segment_duration = segment_duration
        self.mode = mode
        self.resolution = resolution
        self.scale_crop = scale_crop

    def run(self):
        try:
            filename = os.path.splitext(os.path.basename(self.input_path))[0]
            ext = os.path.splitext(self.input_path)[1]
            
            # Check for FFmpeg in Windows
            ffmpeg_path = self.get_ffmpeg_path()
            if not ffmpeg_path:
                self.error.emit("❌ FFmpeg не знайдено! Переконайтеся що ffmpeg.exe знаходиться в тій же папці що і програма")
                return
            
            # Get video info first
            self.progress.emit("📏 Визначення параметрів відео...")
            duration_cmd = [
                ffmpeg_path + "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", self.input_path
            ]
            
            # Get video resolution
            resolution_cmd = [
                ffmpeg_path + "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0", self.input_path
            ]
            
            result = subprocess.run(duration_cmd, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                self.error.emit("❌ Не вдалося визначити тривалість відео")
                return
                
            total_duration = float(result.stdout.strip())
            
            res_result = subprocess.run(resolution_cmd, capture_output=True, text=True, shell=True)
            original_resolution = res_result.stdout.strip() if res_result.returncode == 0 else "1920x1080"
            
            self.progress.emit(f"📊 Оригінальна роздільна здатність: {original_resolution}")
            
            # Calculate target resolution
            target_width, target_height = self.calculate_target_resolution(original_resolution, self.resolution)
            if target_width and target_height:
                self.progress.emit(f"📊 Цільова роздільна здатність: {target_width}x{target_height}")
            
            num_segments = int(total_duration // self.segment_duration) + 1
            self.progress.emit(f"📊 Тривалість: {total_duration:.1f} сек, Сегментів: {num_segments}")
            
            # Add scale filter to commands if resolution change is needed
            scale_filter = ""
            if self.resolution != "original":
                if self.scale_crop:
                    # Full frame with crop
                    scale_filter = f"-vf scale={target_width}x{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}"
                    self.progress.emit("📐 Режим масштабування: Full frame з обрізкою")
                else:
                    # Fit with black bars
                    scale_filter = f"-vf scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
                    self.progress.emit("📐 Режим масштабування: Вмістити з чорними смугами")
                    
                # Force re-encoding mode when resolution change is needed
                if self.mode == "fast":
                    self.progress.emit("⚡ Зміна роздільної здатності потребує перекодування. Перемикаю на точний режим...")
                    self.mode = "precise"
            
            if self.mode == "fast":
                # Fast mode - stream copy with accurate splitting
                self.progress.emit("⚡ Швидкий режим: нарізка без перекодування...")
                
                for i in range(num_segments):
                    start_time = i * self.segment_duration
                    
                    # Calculate duration for this segment
                    remaining_time = total_duration - start_time
                    if remaining_time <= 0:
                        break
                    elif remaining_time < self.segment_duration:
                        # Last segment - use whatever time is left
                        duration = remaining_time
                    else:
                        duration = self.segment_duration
                    
                    output_file = os.path.join(self.output_dir, f"{filename}_{i:03d}{ext}")
                    
                    cmd = [
                        ffmpeg_path + "ffmpeg",
                        "-accurate_seek",
                        "-ss", str(start_time),
                        "-i", self.input_path,
                        "-t", str(duration),
                        "-c", "copy",
                        "-map", "0:v",
                        "-map", "0:a",
                    ] + (scale_filter.split() if scale_filter else []) + [
                        output_file
                    ]
                    
                    self.progress.emit(f"🎬 Створення сегмента {i+1} (0:{int(start_time):02d} - 0:{int(start_time + duration):02d}, {duration:.1f} сек)")
                    
                    process = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    
                    if process.returncode != 0:
                        self.progress.emit(f"⚠️ Попередження для сегмента {i+1}: {process.stderr}")
                    else:
                        self.progress.emit(f"✅ Сегмент {i+1} готовий")
                    
                    self.segment_progress.emit(int((i + 1) / num_segments * 100))
                    
                    if start_time >= total_duration:
                        break
                        
            else:
                # Precise mode - re-encoding
                self.progress.emit("🎯 Точний режим: перекодування...")
                
                for i in range(num_segments):
                    start_time = i * self.segment_duration
                    
                    # Calculate duration for this segment
                    remaining_time = total_duration - start_time
                    if remaining_time <= 0:
                        break
                    elif remaining_time < self.segment_duration:
                        # Last segment - use whatever time is left
                        duration = remaining_time
                    else:
                        duration = self.segment_duration
                    
                    output_file = os.path.join(self.output_dir, f"{filename}_{i:03d}.mp4")
                    
                    cmd = [
                        ffmpeg_path + "ffmpeg",
                        "-accurate_seek",
                        "-ss", str(start_time),
                        "-i", self.input_path,
                        "-t", str(duration),
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        "-preset", "medium",
                        "-crf", "23",
                        "-b:a", "192k",
                        "-map", "0:v",
                        "-map", "0:a",
                        "-movflags", "+faststart",
                    ] + (scale_filter.split() if scale_filter else []) + [
                        output_file
                    ]
                    
                    self.progress.emit(f"🎬 Створення сегмента {i+1} (0:{int(start_time):02d} - 0:{int(start_time + duration):02d}, {duration:.1f} сек)")
                    
                    process = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    
                    if process.returncode != 0:
                        self.error.emit(f"❌ Помилка сегмента {i+1}: {process.stderr}")
                        return
                    else:
                        self.progress.emit(f"✅ Сегмент {i+1} готовий")
                    
                    self.segment_progress.emit(int((i + 1) / num_segments * 100))
                    
                    if start_time >= total_duration:
                        break

            self.finished.emit(True, f"✅ Готово! Файли збережено в: {self.output_dir}")

        except Exception as e:
            self.error.emit(f"❌ Помилка: {str(e)}")

    def get_ffmpeg_path(self):
        """Get FFmpeg path for Windows"""
        # Check if ffmpeg.exe exists in the same directory
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
        ffmpeg_exe = os.path.join(current_dir, "ffmpeg.exe")
        
        if os.path.exists(ffmpeg_exe):
            return current_dir + os.sep
        
        # Check if we're running from a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            bundle_dir = os.path.dirname(sys.executable)
            ffmpeg_exe = os.path.join(bundle_dir, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                return bundle_dir + os.sep
        
        # Check current directory
        if os.path.exists("ffmpeg.exe"):
            return ""
        
        # Check system PATH
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return ""
        except:
            return None

    def calculate_target_resolution(self, original_res, target_ratio):
        """Calculate target resolution based on aspect ratio"""
        if target_ratio == "original":
            return None, None
            
        # Parse original resolution
        try:
            orig_width, orig_height = map(int, original_res.split('x'))
        except:
            orig_width, orig_height = 1920, 1080
            
        # Calculate target dimensions
        if target_ratio == "9:16":  # Vertical
            target_height = min(orig_height, 1920)
            target_width = int(target_height * 9 / 16)
        elif target_ratio == "4:5":  # Instagram portrait
            target_height = min(orig_height, 1350)
            target_width = int(target_height * 4 / 5)
        elif target_ratio == "1:1":  # Square
            target_size = min(orig_width, orig_height, 1080)
            target_width = target_height = target_size
        elif target_ratio == "16:9":  # Horizontal
            target_width = min(orig_width, 1920)
            target_height = int(target_width * 9 / 16)
        else:
            return None, None
            
        return target_width, target_height


class VideoSplitterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.worker_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Splitter - Нарізка відео")
        self.setGeometry(100, 100, 600, 550)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🎬 Video Splitter")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        
        # File selection area
        file_frame = QFrame()
        file_frame.setFrameStyle(QFrame.Box)
        file_frame.setStyleSheet("QFrame { border: 2px dashed #ccc; border-radius: 10px; padding: 20px; }")
        file_layout = QVBoxLayout(file_frame)
        
        self.file_label = QLabel("📁 Перетягніть відеофайл сюди або оберіть файл")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setStyleSheet("color: #666; font-size: 14px;")
        file_layout.addWidget(self.file_label)
        
        select_btn = QPushButton("📂 Обрати файл")
        select_btn.clicked.connect(self.select_file)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        file_layout.addWidget(select_btn)
        
        layout.addWidget(file_frame)
        
        # Settings area
        settings_frame = QFrame()
        settings_layout = QVBoxLayout(settings_frame)
        
        # Duration setting
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("⏱️ Тривалість сегменту (сек):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3600)
        self.duration_spin.setValue(60)
        self.duration_spin.setStyleSheet("QSpinBox { font-size: 14px; padding: 5px; }")
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        settings_layout.addLayout(duration_layout)
        
        # Resolution setting
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("📐 Роздільна здатність:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Оригінальна",
            "16:9 (Горизонтальна)",
            "9:16 (Вертикальна)", 
            "4:5 (Instagram)",
            "1:1 (Квадрат)"
        ])
        self.resolution_combo.setStyleSheet("QComboBox { font-size: 14px; padding: 5px; }")
        resolution_layout.addWidget(self.resolution_combo)
        resolution_layout.addStretch()
        settings_layout.addLayout(resolution_layout)
        
        # Scale option setting
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("🔍 Масштабування:"))
        self.scale_checkbox = QCheckBox("Full frame (з обрізкою країв)")
        self.scale_checkbox.setChecked(True)
        self.scale_checkbox.setStyleSheet("QCheckBox { font-size: 14px; }")
        scale_layout.addWidget(self.scale_checkbox)
        scale_layout.addStretch()
        settings_layout.addLayout(scale_layout)
        
        # Mode selection
        mode_label = QLabel("⚙️ Режим нарізки:")
        mode_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        settings_layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        
        self.fast_radio = QRadioButton("⚡ Швидкий (без перекодування)")
        self.fast_radio.setChecked(True)
        self.fast_radio.setStyleSheet("QRadioButton { font-size: 14px; }")
        self.mode_group.addButton(self.fast_radio, 0)
        settings_layout.addWidget(self.fast_radio)
        
        fast_desc = QLabel("   Дуже швидко, зберігає оригінальну якість")
        fast_desc.setStyleSheet("color: #666; font-size: 12px; margin-left: 20px;")
        settings_layout.addWidget(fast_desc)
        
        self.precise_radio = QRadioButton("🎯 Точний (з перекодуванням)")
        self.precise_radio.setStyleSheet("QRadioButton { font-size: 14px; }")
        self.mode_group.addButton(self.precise_radio, 1)
        settings_layout.addWidget(self.precise_radio)
        
        precise_desc = QLabel("   Точно по часу, перекодування в MP4")
        precise_desc.setStyleSheet("color: #666; font-size: 12px; margin-left: 20px;")
        settings_layout.addWidget(precise_desc)
        
        layout.addWidget(settings_frame)
        
        # Start button
        self.start_btn = QPushButton("🚀 START")
        self.start_btn.clicked.connect(self.start_splitting)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; }")
        layout.addWidget(self.progress_bar)
        
        # Log area
        log_label = QLabel("📋 Лог виконання:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Enable drag & drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if os.path.isfile(file_path):
                self.set_input_file(file_path)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Оберіть відеофайл",
            "",
            "Відеофайли (*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm);;Усі файли (*)"
        )
        if file_path:
            self.set_input_file(file_path)

    def set_input_file(self, file_path):
        self.input_path = file_path
        filename = os.path.basename(file_path)
        self.file_label.setText(f"📹 Обрано: {filename}")
        self.file_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.log_text.clear()

    def start_splitting(self):
        if not self.input_path:
            return

        # Create output directory
        folder = os.path.dirname(self.input_path)
        filename = os.path.splitext(os.path.basename(self.input_path))[0]
        output_dir = os.path.join(folder, filename)
        
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.log_text.append(f"❌ Помилка створення папки: {e}")
            return

        # Get settings
        segment_duration = self.duration_spin.value()
        mode = "fast" if self.fast_radio.isChecked() else "precise"
        
        # Get resolution setting
        resolution_map = {
            "Оригінальна": "original",
            "16:9 (Горизонтальна)": "16:9", 
            "9:16 (Вертикальна)": "9:16",
            "4:5 (Instagram)": "4:5",
            "1:1 (Квадрат)": "1:1"
        }
        resolution = resolution_map[self.resolution_combo.currentText()]
        scale_crop = self.scale_checkbox.isChecked()

        # Update UI
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.log_text.append(f"🎬 Початок нарізки відео...")
        self.log_text.append(f"📁 Вихідний файл: {self.input_path}")
        self.log_text.append(f"📂 Папка призначення: {output_dir}")
        self.log_text.append(f"⏱️ Тривалість сегменту: {segment_duration} сек")
        self.log_text.append(f"📐 Роздільна здатність: {self.resolution_combo.currentText()}")
        scale_mode = "Full frame (з обрізкою)" if self.scale_checkbox.isChecked() else "Вмістити з чорними смугами"
        self.log_text.append(f"🔍 Масштабування: {scale_mode}")
        self.log_text.append(f"⚙️ Режим: {'Швидкий' if mode == 'fast' else 'Точний'}")
        self.log_text.append("")

        # Start worker thread
        self.worker_thread = WorkerThread(self.input_path, output_dir, segment_duration, mode, resolution, scale_crop)
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.segment_progress.connect(self.update_segment_progress)
        self.worker_thread.finished.connect(self.on_finished)
        self.worker_thread.error.connect(self.on_error)
        self.worker_thread.start()

    def update_progress(self, message):
        self.log_text.append(message)

    def update_segment_progress(self, value):
        self.progress_bar.setValue(value)

    def on_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.log_text.append("")
        self.log_text.append(message)

    def on_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.log_text.append("")
        self.log_text.append(error_message)
        
        # Show error dialog for critical errors
        if "FFmpeg не знайдено" in error_message:
            QMessageBox.critical(self, "Помилка FFmpeg", 
                "FFmpeg не знайдено!\n\n"
                "Будь ласка, переконайтеся що ffmpeg.exe знаходиться в тій же папці що і програма.\n"
                "Або завантажте FFmpeg з https://ffmpeg.org/download.html")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = VideoSplitterApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
