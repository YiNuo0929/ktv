import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout, QProgressBar,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# -------------------- QThread 任務處理 --------------------
class KTVWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, audio_path, output_dir="output", bg_image="black.jpg"):
        super().__init__()
        self.audio_path = audio_path
        self.output_dir = output_dir
        self.bg_image = bg_image

    def run(self):
        try:
            self.progress_signal.emit(10)
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            basename = os.path.splitext(os.path.basename(self.audio_path))[0]
            output_video = os.path.join(self.output_dir, f"{basename}_video.mp4")

            env = os.environ.copy()
            env["KTV_BG_IMAGE"] = self.bg_image

            process = subprocess.Popen(
                ["python", "ktv_tool.py", "--input", self.audio_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            for line in iter(process.stdout.readline, ''):
                print("[LOG]", line.strip())  # 可選：在終端印出來除錯
                if "分離人聲與伴奏" in line:
                    self.progress_signal.emit(30)
                elif "生成字幕檔" in line:
                    self.progress_signal.emit(60)
                elif "合成 KTV 影片" in line:
                    self.progress_signal.emit(90)

            process.stdout.close()
            process.wait()

            if process.returncode == 0:
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, output_video)
            else:
                self.finished_signal.emit(False, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


# -------------------- 主視窗介面 --------------------
class KTVApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("KTV 製作工具")
        self.setGeometry(100, 100, 500, 320)

        self.label = QLabel("請選擇音訊檔案：")
        self.label.setAlignment(Qt.AlignCenter)

        self.btnSelect = QPushButton("選擇音檔")
        self.btnSelect.clicked.connect(self.openFileDialog)

        self.btnOutput = QPushButton("選擇輸出資料夾")
        self.btnOutput.clicked.connect(self.selectOutputDir)

        self.labelOutput = QLabel("輸出資料夾：output")
        self.labelOutput.setAlignment(Qt.AlignLeft)

        self.btnBG = QPushButton("選擇背景圖片")
        self.btnBG.clicked.connect(self.selectBGImage)

        self.labelBG = QLabel("背景圖片：black.jpg")
        self.labelBG.setAlignment(Qt.AlignLeft)

        self.btnProcess = QPushButton("開始製作 KTV 影片")
        self.btnProcess.clicked.connect(self.processAudio)
        self.btnProcess.setEnabled(False)

        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)

        self.statusLabel = QLabel("目前狀態：等待中")
        self.statusLabel.setAlignment(Qt.AlignLeft)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btnSelect)
        layout.addWidget(self.btnOutput)
        layout.addWidget(self.labelOutput)
        layout.addWidget(self.btnBG)
        layout.addWidget(self.labelBG)
        layout.addWidget(self.btnProcess)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.statusLabel)
        self.setLayout(layout)

        self.audio_path = ""
        self.output_dir = "output"
        self.bg_image = "black.jpg"
        self.worker = None

    def openFileDialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇音訊檔案", "",
                                                   "音訊檔案 (*.mp3 *.m4a *.wav);;所有檔案 (*)",
                                                   options=options)
        if file_path:
            self.audio_path = file_path
            self.label.setText(f"已選擇：{file_path}")
            self.btnProcess.setEnabled(True)

    def selectOutputDir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if dir_path:
            self.output_dir = dir_path
            self.labelOutput.setText(f"輸出資料夾：{dir_path}")

    def selectBGImage(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇背景圖片", "",
                                                   "圖片檔案 (*.jpg *.png);;所有檔案 (*)")
        if file_path:
            self.bg_image = file_path
            self.labelBG.setText(f"背景圖片：{file_path}")

    def processAudio(self):
        if not self.audio_path:
            QMessageBox.warning(self, "錯誤", "請先選擇音訊檔案！")
            return

        self.worker = KTVWorker(self.audio_path, self.output_dir, self.bg_image)
        self.worker.progress_signal.connect(self.updateProgress)
        self.worker.finished_signal.connect(self.processFinished)
        self.worker.start()

    def updateProgress(self, value):
        self.progressBar.setValue(value)
        if value == 30:
            self.statusLabel.setText("目前狀態：🎧 分離人聲與伴奏中...")
        elif value == 60:
            self.statusLabel.setText("目前狀態：📝 生成字幕中...")
        elif value == 90:
            self.statusLabel.setText("目前狀態：🎬 合成影片中...")
        elif value == 100:
            self.statusLabel.setText("目前狀態：✅ 製作完成！")

    def processFinished(self, success, output_video):
        if success:
            QMessageBox.information(self, "成功", f"KTV 影片已產出：\n{output_video}")
        else:
            QMessageBox.critical(self, "錯誤", "KTV 製作失敗！")

        self.btnProcess.setEnabled(True)
        self.progressBar.setValue(0)
        self.statusLabel.setText("目前狀態：等待中")


# -------------------- 主函數 --------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KTVApp()
    ex.show()
    sys.exit(app.exec_())