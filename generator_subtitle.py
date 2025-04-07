from faster_whisper import WhisperModel
from opencc import OpenCC
from tqdm import tqdm
import argparse


# 設定模型與檔案路徑
model = WhisperModel("medium", compute_type="int8")  # 你可換成 tiny 或 medium
cc = OpenCC('s2t')
parser = argparse.ArgumentParser()
parser.add_argument("--input", "-i", required=True, help="人聲音訊檔 (.wav)")
parser.add_argument("--output", "-o", required=True, help="輸出字幕檔 (.srt)")
args = parser.parse_args()

input_audio = args.input
output_srt = args.output

# 執行轉錄
print("🎙️ 開始轉錄音訊（含逐字時間）...")
segments, _ = model.transcribe(input_audio, word_timestamps=True)

# 格式化時間
def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

# 寫入 .srt
with open(output_srt, "w", encoding="utf-8") as f:
    for i, segment in enumerate(tqdm(segments, desc="📝 生成逐字 SRT")):
        words = segment.words
        if not words:
            continue
        start = format_timestamp(words[0].start)  # 🎯 以第一個字的時間為起點
        end = format_timestamp(words[-1].end)
        text = cc.convert("".join([w.word for w in words]).strip())
        f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

print(f"✅ 精確逐字字幕儲存至：{output_srt}")