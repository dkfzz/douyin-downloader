#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用视频下载（yt-dlp 封装）：最高 1080p
- 有多清晰度（含 4K）→ 取 1080p；没有 1080 则取最接近的低一档
- 无清晰度选项 → 直接下载唯一版本
用法:
    python3 dl1080.py <视频链接> [链接2 ...]
例:
    python3 dl1080.py https://www.eporner.com/video-xxxx/yyy/
要求: 安装 yt-dlp + ffmpeg（a-shell 自带，电脑需自行安装）
"""
import sys
import subprocess

FORMAT = "bv*[height<=1080]+ba/b[height<=1080]/b"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 dl1080.py <视频链接> [更多链接]")
        print("例:   python3 dl1080.py https://www.eporner.com/video-xxxx/yyy/")
        return
    for url in sys.argv[1:]:
        print(f"下载: {url}", flush=True)
        r = subprocess.run([
            "yt-dlp",
            "--no-check-certificate",
            "--impersonate", "chrome",
            "--extractor-args", "generic:impersonate",
            "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "-t", "mp4",
            "-f", FORMAT,
            "--retries", "5",
            "--socket-timeout", "30",
            "--no-playlist",
            url,
        ])
        print("完成" if r.returncode == 0 else "失败，换个链接或稍后重试", flush=True)


if __name__ == "__main__":
    main()
