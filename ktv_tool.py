import argparse
import subprocess
import os
import sys
import glob
from yt_downloader import MusicDownloader

# === 主流程：從 YouTube 下載並執行 inference、subtitle、ktv_video ===
def run_pipeline(youtube_url):
#def run_pipeline(youtube_url, gpu_id=-1): #use gpu mode
    print("🎵 偵測到 YouTube 連結，自動下載音樂中...")
    sys.stdout.flush()

    # 下載音樂
    downloader = MusicDownloader()
    input_path = downloader.download_music(youtube_url)
    downloader.close_driver()

    basename = os.path.splitext(os.path.basename(input_path))[0]

    os.makedirs("output", exist_ok=True)

    # Step 1️⃣ 執行 inference.py 進行人聲分離
    print("\n分離人聲與伴奏"); sys.stdout.flush()
    subprocess.run([
        "python", "inference.py",
        "--input", input_path
    ], check=True)
    '''
    #gpu mode
    subprocess.run([
    "python", "inference.py",
    "--input", input_path,
    "--gpu", str(gpu_id)   # ✅ 加上這個
    ], check=True)
    '''

    # Step 2️⃣ 執行 generator_subtitle.py 產生字幕
    print("\n生成字幕檔"); sys.stdout.flush()
    subprocess.run([
        "python", "generator_subtitle.py",
        "--input", f"output/{basename}_Vocals.wav",
        "--output", f"output/{basename}_subtitle.srt"
    ], check=True)

    # Step 3️⃣ 執行 ktv_video.py 合成 KTV 影片
    print("\n合成 KTV 影片"); sys.stdout.flush()
    subprocess.run([
        "python", "ktv_video.py",
        "--input_audio", f"output/{basename}_Instruments.wav",
        "--input_subtitle", f"output/{basename}_subtitle.srt",
        "--output_video", f"output/{basename}_video.mp4"
    ], check=True)

    print(f"\n✅ 全部完成！已產出影片：output/{basename}_video.mp4"); sys.stdout.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="YouTube 音樂網址")
    args = parser.parse_args()

    run_pipeline(args.input)
    '''
    gpu mode
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="YouTube 音樂網址")
    parser.add_argument("--gpu", type=int, default=-1, help="GPU 編號，-1 表示使用 CPU")
    args = parser.parse_args()

    run_pipeline(args.input, gpu_id=args.gpu)
    '''