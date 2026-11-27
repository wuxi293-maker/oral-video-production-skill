#!/usr/bin/env python3
"""字幕条稳定性检查：找出字幕区域内文字明显变少/变空的帧。

原理：
  字幕条底色和纹理基本稳定，文字会带来较高的边缘能量。
  逐帧计算字幕区域的边缘能量，和前后几帧的中位数比较；
  明显低于邻域中位数的帧，判为“低文字帧/疑似空白帧”，
  再输出联系表供人工确认是否真的闪空。

用法：
  python3 qc_captions.py final.mp4 --json-out caption_qc.json --contact-sheet caption_qc.jpg

  # 自定义区域 x,y,w,h；默认 TP02：120,1132,840,94
  python3 qc_captions.py final.mp4 --region 120,1132,840,94

注意：
  - 这是启发式检查，不是 OCR；低文字帧必须回看联系表确认。
  - 字幕文字瞬时切换时，单帧边缘能量变化是正常的；只有“接近空白”才应报警。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


def which(name: str, override: str | None) -> str:
    if override:
        p = Path(override)
        if p.exists():
            return str(p)
        raise SystemExit(f"[ERROR] 找不到 {name}: {override}")
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"[ERROR] 找不到 {name}，请先安装 ffmpeg。")
    return found


def parse_region(value: str) -> tuple[int, int, int, int]:
    parts = [int(x.strip()) for x in value.split(",")]
    if len(parts) != 4:
        raise SystemExit("[ERROR] --region 需要 x,y,w,h 四个整数")
    x, y, w, h = parts
    if w <= 0 or h <= 0:
        raise SystemExit("[ERROR] --region 宽高必须为正")
    return x, y, w, h


def read_gray_frames(
    ffmpeg: str, video: str, region: tuple[int, int, int, int], sample_width: int
) -> tuple[np.ndarray, int, int]:
    x, y, w, h = region
    sample_h = max(8, round(sample_width * h / w))
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video,
        "-vf",
        f"crop={w}:{h}:{x}:{y},scale={sample_width}:{sample_h},format=gray",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if p.returncode != 0:
        raise SystemExit(f"[ERROR] ffmpeg 取帧失败:\n{p.stderr.decode('utf-8', 'replace')[:2000]}")
    frame_size = sample_width * sample_h
    n = len(p.stdout) // frame_size
    if n == 0:
        raise SystemExit("[ERROR] 没有读到帧，检查 --region 是否超出画面")
    frames = np.frombuffer(p.stdout[: n * frame_size], dtype=np.uint8).reshape(n, sample_h, sample_width)
    return frames, sample_width, sample_h


def edge_energy(frames: np.ndarray) -> np.ndarray:
    # 水平 + 垂直梯度均值；文字边缘会显著抬高该值
    dx = np.abs(np.diff(frames.astype(np.float32), axis=2)).mean(axis=(1, 2))
    dy = np.abs(np.diff(frames.astype(np.float32), axis=1)).mean(axis=(1, 2))
    return (dx + dy) / 2.0


def find_low_text_frames(edge: np.ndarray, window: int, ratio: float) -> tuple[list[dict[str, Any]], np.ndarray]:
    n = len(edge)
    med = np.zeros(n, dtype=np.float32)
    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        neighbors = [edge[j] for j in range(lo, hi) if j != i]
        med[i] = float(np.median(neighbors)) if neighbors else float(edge[i])
    flags: list[dict[str, Any]] = []
    for i in range(n):
        m = float(med[i])
        if m > 1.0 and float(edge[i]) < ratio * m:
            flags.append(
                {
                    "frame": i,
                    "time": round(i / 30.0, 3),
                    "edge": round(float(edge[i]), 3),
                    "neighborMedian": round(m, 3),
                    "ratio": round(float(edge[i]) / m, 3),
                }
            )
    return flags, med


def cluster_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not flags:
        return []
    clusters: list[dict[str, Any]] = []
    cur = [flags[0]]
    for f in flags[1:]:
        if f["frame"] == cur[-1]["frame"] + 1:
            cur.append(f)
        else:
            clusters.append(_make_cluster(cur))
            cur = [f]
    clusters.append(_make_cluster(cur))
    return clusters


def _make_cluster(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "startFrame": items[0]["frame"],
        "endFrame": items[-1]["frame"],
        "start": items[0]["time"],
        "end": items[-1]["time"],
        "frames": len(items),
        "minEdge": min(i["edge"] for i in items),
        "maxRatio": max(i["ratio"] for i in items),
    }


def write_contact_sheet(
    ffmpeg: str, video: str, region: tuple[int, int, int, int], frames: list[int], out: str
) -> None:
    x, y, w, h = region
    select = "+".join(f"eq(n,{i})" for i in frames)
    n = len(frames)
    vf = f"select='{select}',crop={w}:{h}:{x}:{y},scale=420:-1,tile=1x{n}"
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video,
        "-vf",
        vf,
        "-frames:v",
        "1",
        out,
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if p.returncode != 0:
        raise SystemExit(f"[ERROR] 生成联系表失败:\n{p.stderr.decode('utf-8', 'replace')[:2000]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="字幕条空白/低文字帧检查")
    ap.add_argument("video")
    ap.add_argument("--preset", choices=["tp02"], default="tp02", help="内置区域预设；默认 TP02")
    ap.add_argument("--region", default=None, help="自定义 x,y,w,h；默认 TP02 120,1132,840,94")
    ap.add_argument("--sample-width", type=int, default=420)
    ap.add_argument("--window", type=int, default=3, help="邻域半径（帧）")
    ap.add_argument("--ratio", type=float, default=0.55, help="低于邻域中位数的比例即报警")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--contact-sheet", default=None)
    ap.add_argument("--ffmpeg", default=None)
    args = ap.parse_args()

    video = str(Path(args.video).expanduser().resolve())
    if not Path(video).is_file():
        raise SystemExit(f"[ERROR] 文件不存在: {video}")

    if args.region:
        region = parse_region(args.region)
    else:
        region = (120, 1132, 840, 94)
        if args.preset != "tp02":
            raise SystemExit("[ERROR] 目前只内置 TP02 字幕区，请用 --region 指定")

    ffmpeg = which("ffmpeg", args.ffmpeg)
    frames, sw, sh = read_gray_frames(ffmpeg, video, region, args.sample_width)
    edge = edge_energy(frames)
    flags, med = find_low_text_frames(edge, args.window, args.ratio)
    clusters = cluster_flags(flags)

    report: dict[str, Any] = {
        "video": video,
        "region": {"x": region[0], "y": region[1], "w": region[2], "h": region[3]},
        "sampled": {"width": sw, "height": sh, "frames": int(len(frames))},
        "method": "edge-energy vs neighbor median",
        "ratio": args.ratio,
        "window": args.window,
        "flaggedFrames": flags,
        "clusters": clusters,
        "passed": len(clusters) == 0,
        "note": "低文字帧必须回看联系表确认；字幕瞬时换字造成的单帧变化不等同于闪空。",
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.contact_sheet and flags:
        # 每个簇取首帧，最多 20 帧；太多则取前 20 个簇
        picks = [c["startFrame"] for c in clusters[:20]]
        write_contact_sheet(ffmpeg, video, region, picks, args.contact_sheet)
        report["contactSheet"] = str(Path(args.contact_sheet).resolve())
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    print(f"\n视频: {video}")
    print(f"字幕区: {region[2]}x{region[3]} @ ({region[0]},{region[1]})  帧数: {len(frames)}")
    if clusters:
        print(f"结果: FAIL  发现 {len(clusters)} 段低文字/疑似空白帧")
        for c in clusters[:20]:
            print(
                f"  - 帧 {c['startFrame']}-{c['endFrame']} / {c['start']:.3f}-{c['end']:.3f}s  "
                f"{c['frames']} 帧  minEdge={c['minEdge']}  maxRatio={c['maxRatio']}"
            )
        if len(clusters) > 20:
            print(f"  ... 其余 {len(clusters)-20} 段见 JSON")
    else:
        print("结果: PASS  未发现明显的字幕空白帧")
    if args.contact_sheet and flags:
        print(f"联系表: {Path(args.contact_sheet).resolve()}  （逐帧回看确认）")
    print("\n注意: 这是启发式检查；最终以联系表/逐帧回看为准。")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
