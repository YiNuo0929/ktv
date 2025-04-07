import argparse
import os
import sys
import glob
import subprocess
from yt_downloader import MusicDownloader
from inference import main as run_inference

from faster_whisper import WhisperModel
from opencc import OpenCC

def generate_subtitles(input_audio, output_srt):
    model = WhisperModel("medium", compute_type="int8")
    cc = OpenCC('s2t')
    print("🎙️ 開始轉錄音訊（含逐字時間）...")
    segments, _ = model.transcribe(input_audio, word_timestamps=True)

    def format_timestamp(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

    with open(output_srt, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments):
            words = segment.words
            if not words:
                continue
            start = format_timestamp(words[0].start)
            end = format_timestamp(words[-1].end)
            text = cc.convert("".join([w.word for w in words]).strip())
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

    print(f"✅ 精確逐字字幕儲存至：{output_srt}")

def generate_ktv_video(audio_path, subtitle_path, output_path, bg_image="black.jpg"):
    if not os.path.exists(bg_image):
        raise FileNotFoundError("❌ 找不到背景圖片 black.jpg")

    print("🎬 開始合成 KTV 字幕影片...")
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "2", "-i", bg_image,
        "-i", audio_path,
        "-vf", f"subtitles={subtitle_path}",
        "-shortest", "-c:v", "libx264", "-c:a", "aac",
        "-strict", "-2", "-b:a", "192k", "-pix_fmt", "yuv420p",
        output_path
    ])
    print(f"🎉 完成！影片已儲存為：{output_path}")


def run_pipeline(youtube_url):
    print("🎵 偵測到 YouTube 連結，自動下載音樂中...")
    sys.stdout.flush()

    downloader = MusicDownloader()
    input_path = downloader.download_music(youtube_url)
    downloader.close_driver()

    basename = os.path.splitext(os.path.basename(input_path))[0]
    os.makedirs("output", exist_ok=True)

    print("\n分離人聲與伴奏"); sys.stdout.flush()
    sys.argv = ["inference.py", "--input", input_path, "--output_dir", "output"]
    '''
    gpu mode
    sys.argv = [
    "inference.py",
    "--input", input_path,
    "--output_dir", "output",
    "--gpu", "0"  # ✅ 啟用 GPU
    ]
    run_inference()
    '''
    run_inference()

    print("\n生成字幕檔"); sys.stdout.flush()
    generate_subtitles(
        input_audio=f"output/{basename}_Vocals.wav",
        output_srt=f"output/{basename}_subtitle.srt"
    )

    print("\n合成 KTV 影片"); sys.stdout.flush()
    generate_ktv_video(
        audio_path=f"output/{basename}_Instruments.wav",
        subtitle_path=f"output/{basename}_subtitle.srt",
        output_path=f"output/{basename}_video.mp4",
        bg_image=os.environ.get("KTV_BG_IMAGE", "black.jpg")
    )

    print(f"\n✅ 全部完成！已產出影片：output/{basename}_video.mp4")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="YouTube 音樂網址")
    args = parser.parse_args()
    run_pipeline(args.input)