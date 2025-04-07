import subprocess
import os
import argparse

# 檔案路徑設定
import os
bg_image = os.environ.get("KTV_BG_IMAGE", "black.jpg")  # 預設仍是 black.jpg
parser = argparse.ArgumentParser()
parser.add_argument("--input_audio", "-a", required=True)
parser.add_argument("--input_subtitle", "-s", required=True)
parser.add_argument("--output_video", "-o", required=True)
args = parser.parse_args()

audio_path = args.input_audio
subtitle_path = args.input_subtitle
output_video = args.output_video

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