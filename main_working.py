#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QRadioButton, QButtonGroup, 
                              QSpinBox, QLabel, QTextEdit, QFileDialog, QProgressBar,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette, QColor


class WorkerThread(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, input_path, output_dir, segment_duration, mode):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.segment_duration = segment_duration
        self.mode = mode

    def run(self):
        try:
            filename = os.path.splitext(os.path.basename(self.input_path))[0]
            ext = os.path.splitext(self.input_path)[1]
            
            if self.mode == "fast":
                # Fast mode - stream copy
                output_pattern = os.path.join(self.output_dir, f"{filename}_%03d{ext}")
                cmd = [
                    "ffmpeg",
                    "-i", self.input_path,
                    "-c", "copy",
                    "-map", "0:v",  # video stream
                    "-map", "0:a",  # audio stream
                    "-segment_time", str(self.segment_duration),
                    "-f", "segment",
                    output_pattern
                ]
            else:
                # Precise mode - re-encoding with exact time splitting
                output_pattern = os.path.join(self.output_dir, f"{filename}_%03d.mp4")
                
                # Generate segments using -ss and -t for exact timing
                cmd = [
                    "ffmpeg",
                    "-i", self.input_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-preset", "medium",
                    "-crf", "23",
                    "-b:a", "192k",
                    "-map", "0:v",
                    "-map", "0:a",
                    "-f", "segment",
                    "-segment_time", str(self.segment_duration),
                    "-segment_format_options", "movflags=faststart",
                    "-reset_timestamps", "1",
                    "-break_non_keyframes", "1",
                    output_pattern
                ]

            self.progress.emit(f"Запуск команди:\n{' '.join(cmd)}\n")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.progress.emit(output.strip())

            return_code = process.poll()
            
            if return_code == 0:
                self.finished.emit(True, f"✅ Готово! Файли збережено в: {self.output_dir}")
            else:
                self.finished.emit(False, f"❌ Помилка FFmpeg з кодом {return_code}")

        except Exception as e:
            self.error.emit(f"❌ Помилка: {str(e)}")


class VideoSplitterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.worker_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Splitter - Нарізка відео")
        self.setGeometry(100, 100, 600, 500)
        
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
        
        fast_desc = QLabel("   Дуже швидко, ріже по ключових кадрах")
        fast_desc.setStyleSheet("color: #666; font-size: 12px; margin-left: 20px;")
        settings_layout.addWidget(fast_desc)
        
        self.precise_radio = QRadioButton("🎯 Точний (з перекодуванням)")
        self.precise_radio.setStyleSheet("QRadioButton { font-size: 14px; }")
        self.mode_group.addButton(self.precise_radio, 1)
        settings_layout.addWidget(self.precise_radio)
        
        precise_desc = QLabel("   Ріже точно по часу, повільніше, завжди MP4")
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

        # Update UI
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.log_text.clear()
        self.log_text.append(f"🎬 Початок нарізки відео...")
        self.log_text.append(f"📁 Вихідний файл: {self.input_path}")
        self.log_text.append(f"📂 Папка призначення: {output_dir}")
        self.log_text.append(f"⏱️ Тривалість сегменту: {segment_duration} сек")
        self.log_text.append(f"⚙️ Режим: {'Швидкий' if mode == 'fast' else 'Точний'}")
        self.log_text.append("")

        # Start worker thread
        self.worker_thread = WorkerThread(self.input_path, output_dir, segment_duration, mode)
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.finished.connect(self.on_finished)
        self.worker_thread.error.connect(self.on_error)
        self.worker_thread.start()

    def update_progress(self, message):
        self.log_text.append(message)

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
