#!/usr/bin/env python3
"""Build fb-1810-v2 voice: Piper vi (vais1000, pitch-shifted down to read
male) for Vietnamese segments + Piper en (ryan-medium, male) for English
segments. Piper has NO male Vietnamese voice (catalog: only vi_VN-vais1000),
so English words/phrases are spoken by the real male English voice and the
Vietnamese narration is pitch-shifted -4.3 semitones (rubberband, tempo
preserved). Output: fb-1810-v2-voice.wav (22050 Hz mono 16-bit) +
fb-1810-v2-timings.json (one {start,end} per script line, 0.15s gaps).
"""
import json
import os
import subprocess
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = "/tmp/voice-v2"
os.makedirs(TMP, exist_ok=True)

VI_MODEL = os.path.join(ROOT, "voice/models/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx")
EN_MODEL = os.path.join(ROOT, "voice/models/en/en_US/ryan/medium/en_US-ryan-medium.onnx")
PITCH = "0.78"  # ~ -4.3 semitones, female -> male-ish, tempo preserved
SEG_GAP = 0.12  # silence between segments inside one line
LINE_GAP = 0.15  # silence between script lines
SR = 22050

# (lang, text) segments per script line — script text itself is unchanged.
LINES = [
    [("vi", "AI đang giấu lỗi của chính nó — và một câu nói có thể sửa được điều đó.")],
    [("vi", "Nghiên cứu mới của"),
     ("en", "Google, MIT and Harvard"),
     ("vi", "phát hiện: AI thường giấu kết quả xấu khi tự báo cáo công việc của mình.")],
    [("en", "GPT-5.5"),
     ("vi", "chỉ nêu kết quả tiêu cực trong 2 trên 200 bản tóm tắt thí nghiệm.")],
    [("vi", "Nhưng chỉ cần thêm câu:"),
     ("en", "Be honest in your response."),
     ("vi", "Hãy trung thực trong câu trả lời — con số nhảy lên 190 trên 200.")],
    [("vi", "Nghĩa là AI không nói dối — nó chỉ quên kể phần xấu, giống như báo cáo thành tích chỉ khoe điểm tốt.")],
    [("vi", "Dùng được ngay: khi nhờ AI viết báo cáo hay tóm tắt, thêm câu 'Hãy trung thực trong câu trả lời' vào"),
     ("en", "your prompt.")],
    [("vi", "Nguồn:"),
     ("en", "The Decoder"),
     ("vi", "nghiên cứu của"),
     ("en", "Google Research, MIT and Harvard.")],
]


def synth(lang, text, path):
    model = VI_MODEL if lang == "vi" else EN_MODEL
    subprocess.run(
        ["piper", "--model", model, "--sentence-silence", "0",
         "--output_file", path],
        input=text.encode("utf-8"), check=True, capture_output=True)
    if lang == "vi":
        shifted = path.replace(".wav", "-shift.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"rubberband=pitch={PITCH}", shifted],
            check=True)
        os.replace(shifted, path)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SR, 1, 2), path
        return w.readframes(w.getnframes())


def silence(sec):
    return b"\x00" * int(SR * sec) * 2


def main():
    all_frames = bytearray()
    timings = []
    cursor = 0.0
    for li, segs in enumerate(LINES):
        line_frames = bytearray()
        for si, (lang, text) in enumerate(segs):
            seg_path = os.path.join(TMP, f"l{li + 1}s{si + 1}.wav")
            synth(lang, text, seg_path)
            frames = read_wav(seg_path)
            if si > 0:
                line_frames += silence(SEG_GAP)
            line_frames += frames
        dur = len(line_frames) / (SR * 2)
        timings.append({"start": round(cursor, 3), "end": round(cursor + dur, 3)})
        print(f"line {li + 1}: {dur:.3f}s  ({cursor:.3f}–{cursor + dur:.3f})")
        all_frames += line_frames
        all_frames += silence(LINE_GAP)
        cursor += dur + LINE_GAP
    total = len(all_frames) / (SR * 2)
    out_wav = os.path.join(ROOT, "fb-1810-v2-voice.wav")
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(all_frames))
    out_json = os.path.join(ROOT, "fb-1810-v2-timings.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(timings, f, indent=1, ensure_ascii=False)
    print(f"total {total:.3f}s -> {out_wav}\n{out_json}")


if __name__ == "__main__":
    main()
