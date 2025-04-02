import subprocess
import os

# 檔案路徑設定
bg_image = "black.jpg"
audio_path = "output/five_Instruments.wav"
subtitle_path = "output/five_subtitle.srt"
output_video = "output/five_video.mp4"

# 確認黑底圖片存在
if not os.path.exists(bg_image):
    raise FileNotFoundError("❌ 找不到 black.jpg，請先執行 generate_black_background.py 或放入自訂背景圖片。")

# 合成影片
print("🎬 開始合成 KTV 字幕影片...")
subprocess.run([
    "ffmpeg",
    "-loop", "1",
    "-framerate", "2",
    "-i", bg_image,
    "-i", audio_path,
    "-vf", f"subtitles={subtitle_path}",
    "-shortest",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-strict", "-2",
    "-b:a", "192k",
    "-pix_fmt", "yuv420p",
    output_video
])
print(f"🎉 完成！影片已儲存為：{output_video}")