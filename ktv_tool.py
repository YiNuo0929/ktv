import argparse
import subprocess
import os
import sys  # ✅ 加上這行

# === 主流程：全自動依序執行 inference、subtitle、ktv_video ===
def run_pipeline(input_path):
    basename = os.path.splitext(os.path.basename(input_path))[0]
    os.makedirs("output", exist_ok=True)

    # Step 1️⃣ 執行 inference.py 進行人聲分離
    print("\n分離人聲與伴奏"); sys.stdout.flush()  # ✅ 關鍵
    subprocess.run([
        "python", "inference.py",
        "--input", input_path
    ], check=True)

    # Step 2️⃣ 執行 generator_subtitle.py 產生字幕
    print("\n生成字幕檔"); sys.stdout.flush()  # ✅ 關鍵
    subprocess.run([
        "python", "generator_subtitle.py",
        "--input", f"output/{basename}_Vocals.wav",
        "--output", f"output/{basename}_subtitle.srt"
    ], check=True)

    # Step 3️⃣ 執行 ktv_video.py 合成 KTV 影片
    print("\n合成 KTV 影片"); sys.stdout.flush()  # ✅ 關鍵
    subprocess.run([
        "python", "ktv_video.py",
        "--input_audio", f"output/{basename}_Instruments.wav",
        "--input_subtitle", f"output/{basename}_subtitle.srt",
        "--output_video", f"output/{basename}_video.mp4"
    ], check=True)

    print(f"\n✅ 全部完成！已產出影片：output/{basename}_video.mp4"); sys.stdout.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="輸入的音訊檔案（如 song.wav）")
    args = parser.parse_args()

    run_pipeline(args.input)