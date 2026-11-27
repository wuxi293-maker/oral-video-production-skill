#!/usr/bin/env python3
"""技术自检：时长、分辨率、帧率、码率、音轨、黑帧、冻结、音量。

用法：
  python3 qc_video.py final.mp4 --expected-duration 33.6 --json-out qc_report.json

说明：
  - 黑帧是硬失败；冻结默认只告警（慢速 Ken Burns 静图可能误报）。
  - 技术检查通过不等于视觉通过，仍需按 references/self-check.md 人工核对。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def which(name: str, override: str | None) -> str:
    if override:
        p = Path(override)
        if p.exists():
            return str(p)
        raise SystemExit(f"[ERROR] 找不到 {name}: {override}")
    found = shutil.which(name)
    if not found:
        raise SystemExit(
            f"[ERROR] 找不到 {name}。请先安装 ffmpeg，或用 --ffmpeg/--ffprobe 指定路径。"
        )
    return found


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out + "\n[TIMEOUT]"


def probe(ffprobe: str, video: str) -> dict[str, Any]:
    code, out = run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video,
        ],
        timeout=60,
    )
    if code != 0:
        raise SystemExit(f"[ERROR] ffprobe 失败:\n{out}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise SystemExit(f"[ERROR] 无法解析 ffprobe JSON: {e}\n{out[:2000]}")


def frac_to_float(value: str | None) -> float | None:
    if not value:
        return None
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            fa, fb = float(a), float(b)
            return fa / fb if fb else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_black(log: str) -> list[dict[str, float]]:
    # black_start:0 black_end:0.4 black_duration:0.4
    rows = []
    for m in re.finditer(
        r"black_start:\s*([0-9.]+)\s+black_end:\s*([0-9.]+)\s+black_duration:\s*([0-9.]+)",
        log,
    ):
        rows.append(
            {
                "start": float(m.group(1)),
                "end": float(m.group(2)),
                "duration": float(m.group(3)),
            }
        )
    return rows


def parse_freeze(log: str) -> list[dict[str, float]]:
    # freeze_start: 28.4 / freeze_end: 29.5 / freeze_duration: 1.1
    rows = []
    for m in re.finditer(
        r"freeze_start:\s*([0-9.]+)\s+freeze_end:\s*([0-9.]+)\s+freeze_duration:\s*([0-9.]+)",
        log,
    ):
        rows.append(
            {
                "start": float(m.group(1)),
                "end": float(m.group(2)),
                "duration": float(m.group(3)),
            }
        )
    return rows


def parse_volume(log: str) -> dict[str, float | None]:
    mean = re.search(r"mean_volume:\s*(-?[0-9.]+)\s*dB", log)
    peak = re.search(r"max_volume:\s*(-?[0-9.]+)\s*dB", log)
    return {
        "mean": float(mean.group(1)) if mean else None,
        "max": float(peak.group(1)) if peak else None,
    }


def check(
    name: str,
    ok: bool,
    value: Any,
    expected: Any = None,
    detail: str = "",
    hard: bool = True,
) -> dict[str, Any]:
    return {
        "check": name,
        "pass": bool(ok),
        "value": value,
        "expected": expected,
        "detail": detail,
        "hard": hard,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="视频技术自检")
    ap.add_argument("video", help="成片路径")
    ap.add_argument("--expected-duration", type=float, default=None, help="期望时长（秒）")
    ap.add_argument("--duration-tolerance", type=float, default=0.35, help="时长容差（秒）")
    ap.add_argument("--expected-width", type=int, default=1080)
    ap.add_argument("--expected-height", type=int, default=1920)
    ap.add_argument("--expected-fps", type=float, default=30.0)
    ap.add_argument("--fps-tolerance", type=float, default=0.08)
    ap.add_argument("--min-video-bitrate", type=int, default=10_000_000, help="0 表示不检查")
    ap.add_argument("--black-duration", type=float, default=0.10, help="黑帧达到该时长即失败")
    ap.add_argument("--freeze-duration", type=float, default=0.50, help="冻结达到该时长即告警")
    ap.add_argument("--fail-on-freeze", action="store_true", help="冻结也作为硬失败")
    ap.add_argument("--vol-mean-min", type=float, default=-30.0)
    ap.add_argument("--vol-max-min", type=float, default=-8.0)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--ffprobe", default=None)
    args = ap.parse_args()

    video = str(Path(args.video).expanduser().resolve())
    if not Path(video).is_file():
        raise SystemExit(f"[ERROR] 文件不存在: {video}")

    ffmpeg = which("ffmpeg", args.ffmpeg)
    ffprobe = which("ffprobe", args.ffprobe)
    data = probe(ffprobe, video)

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    # 文件
    size = Path(video).stat().st_size
    checks.append(check("file.exists", True, video, detail=f"{size/1024/1024:.1f} MB"))

    fmt = data.get("format", {})
    duration = frac_to_float(str(fmt.get("duration"))) or 0.0
    if duration <= 0:
        failures.append("无法读取视频时长")
    if args.expected_duration is not None:
        ok = abs(duration - args.expected_duration) <= args.duration_tolerance
        checks.append(
            check(
                "duration",
                ok,
                round(duration, 3),
                f"{args.expected_duration} ± {args.duration_tolerance}",
                "与期望时长偏差过大" if not ok else "",
            )
        )
        if not ok:
            failures.append("时长不符合期望")
    else:
        checks.append(check("duration", True, round(duration, 3), detail="未指定期望时长"))

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        failures.append("没有视频流")
        checks.append(check("video.stream", False, None, detail="缺少视频流"))
    else:
        width = to_int(video_stream.get("width")) or 0
        height = to_int(video_stream.get("height")) or 0
        ok = width == args.expected_width and height == args.expected_height
        checks.append(
            check("resolution", ok, f"{width}x{height}", f"{args.expected_width}x{args.expected_height}")
        )
        if not ok:
            failures.append("分辨率不符合期望")

        fps = frac_to_float(video_stream.get("avg_frame_rate")) or frac_to_float(
            video_stream.get("r_frame_rate")
        ) or 0.0
        ok = abs(fps - args.expected_fps) <= args.fps_tolerance
        checks.append(check("fps", ok, round(fps, 3), f"{args.expected_fps} ± {args.fps_tolerance}"))
        if not ok:
            failures.append("帧率不符合期望")

        codec = video_stream.get("codec_name")
        pix = video_stream.get("pix_fmt")
        checks.append(check("video.codec", True, codec, detail=f"pix_fmt={pix}"))
        if pix and pix != "yuv420p":
            warnings.append(f"像素格式为 {pix}，常见平台更兼容 yuv420p")

        vbit = to_int(video_stream.get("bit_rate"))
        if not vbit and fmt.get("bit_rate"):
            vbit = to_int(fmt.get("bit_rate"))
        if args.min_video_bitrate > 0:
            ok = bool(vbit) and vbit >= args.min_video_bitrate
            checks.append(
                check(
                    "video.bitrate",
                    ok,
                    vbit,
                    f"≥ {args.min_video_bitrate}",
                    "码率偏低" if not ok else "",
                )
            )
            if not ok:
                failures.append("视频码率偏低")
        else:
            checks.append(check("video.bitrate", True, vbit, detail="未启用码率检查"))

    if not audio_stream:
        failures.append("没有音频流")
        checks.append(check("audio.stream", False, None, detail="缺少音频流"))
    else:
        sr = to_int(audio_stream.get("sample_rate"))
        ch = to_int(audio_stream.get("channels"))
        acodec = audio_stream.get("codec_name")
        checks.append(
            check("audio.stream", True, f"{acodec}/{sr}Hz/{ch}ch", detail="存在音频流")
        )
        if sr and sr != 48000:
            warnings.append(f"音频采样率 {sr}Hz，交付建议 48kHz")
        if ch and ch != 1 and ch != 2:
            warnings.append(f"音频声道数 {ch}，常见为 1 或 2")

    # 黑帧
    code, log = run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            video,
            "-vf",
            f"blackdetect=d={args.black_duration}:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ],
        timeout=300,
    )
    blacks = parse_black(log)
    bad_blacks = [b for b in blacks if b["duration"] >= args.black_duration]
    checks.append(
        check(
            "blackdetect",
            not bad_blacks,
            bad_blacks,
            f"无 ≥{args.black_duration}s 黑帧",
            "发现黑帧段" if bad_blacks else "",
        )
    )
    if bad_blacks:
        failures.append("发现黑帧段")

    # 冻结
    code, log = run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            video,
            "-vf",
            f"freezedetect=n=0.003:d={args.freeze_duration}",
            "-an",
            "-f",
            "null",
            "-",
        ],
        timeout=300,
    )
    freezes = parse_freeze(log)
    bad_freezes = [f for f in freezes if f["duration"] >= args.freeze_duration]
    checks.append(
        check(
            "freezedetect",
            not (args.fail_on_freeze and bad_freezes),
            bad_freezes,
            "回帧确认：静图慢推可能误报",
            "发现冻结段（告警）" if bad_freezes else "",
            hard=args.fail_on_freeze,
        )
    )
    if bad_freezes:
        if args.fail_on_freeze:
            failures.append("发现冻结段")
        else:
            warnings.append(f"freezedetect 报 {len(bad_freezes)} 段冻结，需回帧确认是否静图慢推")

    # 音量
    code, log = run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            video,
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        timeout=300,
    )
    vol = parse_volume(log)
    mean_ok = vol["mean"] is not None and vol["mean"] >= args.vol_mean_min
    max_ok = vol["max"] is not None and vol["max"] >= args.vol_max_min
    checks.append(
        check(
            "volume.mean",
            mean_ok,
            vol["mean"],
            f"≥ {args.vol_mean_min} dB",
            "平均音量偏低" if not mean_ok else "",
            hard=False,
        )
    )
    checks.append(
        check(
            "volume.max",
            max_ok,
            vol["max"],
            f"≥ {args.vol_max_min} dB",
            "峰值偏低" if not max_ok else "",
            hard=False,
        )
    )
    if vol["mean"] is not None and vol["mean"] < args.vol_mean_min:
        warnings.append("平均音量偏低，人声可能不够清楚")
    if vol["max"] is not None and vol["max"] < args.vol_max_min:
        warnings.append("峰值偏低，成片可能过轻")
    if vol["max"] is not None and vol["max"] > 0.5:
        warnings.append("峰值接近/超过 0dB，可能削波")

    passed = len(failures) == 0
    report = {
        "video": video,
        "sizeBytes": size,
        "duration": round(duration, 3),
        "passed": passed,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "note": "技术通过不等于视觉通过；仍需按 references/self-check.md 做素材对应、素材异常、字幕闪动、抖音安全区检查。",
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n视频: {video}")
    print(f"时长: {duration:.3f}s  大小: {size/1024/1024:.1f} MB  结果: {'PASS' if passed else 'FAIL'}")
    for c in checks:
        mark = "OK" if c["pass"] else ("FAIL" if c["hard"] else "WARN")
        print(f"  [{mark}] {c['check']}: {c['value']}  (期望: {c['expected']})")
    if warnings:
        print("\n告警:")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print("\n失败:")
        for f in failures:
            print(f"  - {f}")
    print("\n注意: 技术检查通过后，仍必须按 references/self-check.md 做四项人工自检。")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
