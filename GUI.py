import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


# -------------------- QThread 任務處理 --------------------
class VocalRemoverWorker(QThread):
    progress_signal = pyqtSignal(int)  # 發送進度
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, audio_path, output_dir="output"):
        super().__init__()
        self.audio_path = audio_path
        self.output_dir = output_dir

    def run(self):
        try:
            # 初始化進度條
            self.progress_signal.emit(10)

            # 確保輸出目錄存在
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            # 設定輸出檔案名稱
            basename = os.path.splitext(os.path.basename(self.audio_path))[0]
            output_vocals = os.path.join(self.output_dir, f"{basename}_Vocals.wav")
            output_instruments = os.path.join(self.output_dir, f"{basename}_Instruments.wav")

            # 執行 inference.py
            process = subprocess.Popen(
                ["python", "inference.py", "--input", self.audio_path, "--output_dir", self.output_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 逐行讀取輸出並更新進度
            for line in process.stdout:
                if "loading model..." in line:
                    self.progress_signal.emit(20)
                elif "loading wave source..." in line:
                    self.progress_signal.emit(40)
                elif "stft of wave source..." in line:
                    self.progress_signal.emit(60)
                elif "inverse stft of instruments..." in line:
                    self.progress_signal.emit(80)
                elif "inverse stft of vocals..." in line:
                    self.progress_signal.emit(90)

            process.wait()

            # 完成分離
            if process.returncode == 0:
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, output_vocals, output_instruments)
            else:
                self.finished_signal.emit(False, "", "")
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")


# -------------------- 主視窗介面 --------------------
class VocalRemoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Vocal Remover GUI")
        self.setGeometry(100, 100, 400, 200)

        # 標籤：顯示選擇的檔案
        self.label = QLabel("請選擇音訊檔案：")
        self.label.setAlignment(Qt.AlignCenter)

        # 按鈕：選擇音檔
        self.btnSelect = QPushButton("選擇音檔")
        self.btnSelect.clicked.connect(self.openFileDialog)

        # 按鈕：開始分離
        self.btnProcess = QPushButton("開始分離")
        self.btnProcess.clicked.connect(self.processAudio)
        self.btnProcess.setEnabled(False)

        # 進度條
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)

        # 版面配置
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btnSelect)
        layout.addWidget(self.btnProcess)
        layout.addWidget(self.progressBar)
        self.setLayout(layout)

        # 初始化
        self.audio_path = ""
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

    def processAudio(self):
        if not self.audio_path:
            QMessageBox.warning(self, "錯誤", "請先選擇音訊檔案！")
            return

        # 設定輸出目錄
        output_dir = "output"

        # 啟動 QThread 來處理推論
        self.worker = VocalRemoverWorker(self.audio_path, output_dir)
        self.worker.progress_signal.connect(self.updateProgress)
        self.worker.finished_signal.connect(self.processFinished)
        self.worker.start()

    def updateProgress(self, value):
        # 更新進度條
        self.progressBar.setValue(value)

    def processFinished(self, success, output_vocals, output_instruments):
        if success:
            QMessageBox.information(self, "成功", f"分離完成！\n人聲：{output_vocals}\n伴奏：{output_instruments}")
        else:
            QMessageBox.critical(self, "錯誤", "音訊分離失敗！")

        # 重置按鈕與進度條
        self.btnProcess.setEnabled(True)
        self.progressBar.setValue(0)


# -------------------- 主函數 --------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VocalRemoverApp()
    ex.show()
    sys.exit(app.exec_())
