#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
野果短剧一键下载+合并（a-shell 手机版，纯 Python 标准库，无需安装任何包）
站点：again.agvibdto.cc / yeguodj.com（同一套后端）

用法：
    python3 yeguo_phone.py 3282
    python3 yeguo_phone.py https://again.agvibdto.cc/drama/detail/3282/

流程：取全集 m3u8 地址 -> ffmpeg 逐集下载 -> 合并成一个 MP4 -> 自动删除分集
（3282 = 《母子同欢》）
"""
import sys, os, json, base64, hashlib, subprocess, re
import urllib.request, urllib.parse

API = "https://www.yeguodj.com/api.php/api/playlet/play"
KEY = b"2acf7e91e9864673"          # AES-128-CBC key
IV  = b"1c29882d3ddfcfd6"           # AES IV
SIGN_KEY = "5589d41f92a597d016b037ac37db243d"
OAUTH_ID = "7d05538c4b8a5e74e82f93c0dab0163c"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
SITE = "https://again.agvibdto.cc/"


# ================= 纯 Python AES-128 解密 =================
_SBOX = (
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
)
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i
_INV_SBOX = tuple(_INV_SBOX)
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def _expand_key(key):
    kb = list(key)
    for i in range(10):
        last = kb[-4:]
        rot = last[1:] + last[:1]
        sub = [_SBOX[b] for b in rot]
        sub[0] ^= _RCON[i]
        for j in range(4):
            kb.append(kb[-16] ^ sub[j])
        for _ in range(12):
            kb.append(kb[-16] ^ kb[-4])
    return [kb[i * 16:(i + 1) * 16] for i in range(11)]


def _inv_shift_rows(s):
    t = [0] * 16
    for r in range(4):
        for c in range(4):
            t[r + 4 * c] = s[r + 4 * ((c - r) % 4)]
    return t


def _inv_mix_columns(s):
    t = [0] * 16
    for c in range(4):
        a0, a1, a2, a3 = s[4 * c], s[4 * c + 1], s[4 * c + 2], s[4 * c + 3]
        t[4 * c]     = _gmul(a0, 0x0e) ^ _gmul(a1, 0x0b) ^ _gmul(a2, 0x0d) ^ _gmul(a3, 0x09)
        t[4 * c + 1] = _gmul(a0, 0x09) ^ _gmul(a1, 0x0e) ^ _gmul(a2, 0x0b) ^ _gmul(a3, 0x0d)
        t[4 * c + 2] = _gmul(a0, 0x0d) ^ _gmul(a1, 0x09) ^ _gmul(a2, 0x0e) ^ _gmul(a3, 0x0b)
        t[4 * c + 3] = _gmul(a0, 0x0b) ^ _gmul(a1, 0x0d) ^ _gmul(a2, 0x09) ^ _gmul(a3, 0x0e)
    return t


def _decrypt_block(block, rks):
    s = [block[i] ^ rks[10][i] for i in range(16)]
    for r in range(9, 0, -1):
        s = _inv_shift_rows(s)
        s = [_INV_SBOX[b] for b in s]
        s = [s[i] ^ rks[r][i] for i in range(16)]
        s = _inv_mix_columns(s)
    s = _inv_shift_rows(s)
    s = [_INV_SBOX[b] for b in s]
    s = [s[i] ^ rks[0][i] for i in range(16)]
    return bytes(s)


def _aes_cbc_decrypt(key, iv, data):
    rks = _expand_key(key)
    out = bytearray()
    prev = iv
    for off in range(0, len(data), 16):
        blk = _decrypt_block(data[off:off + 16], rks)
        out += bytes(b ^ prev[i] for i, b in enumerate(blk))
        prev = data[off:off + 16]
    return bytes(out)


# ================= 接口 =================
def sign(params: dict) -> str:
    items = sorted((k, v) for k, v in params.items()
                   if k not in ("sign", "_ver") and v is not None)
    s = "&".join(f"{k}={v}" for k, v in items) + SIGN_KEY
    return hashlib.md5(hashlib.sha256(s.encode()).hexdigest().encode()).hexdigest()


def api(playlet_id: int, episode_id: int = 0) -> dict:
    params = {"bundleId": "com.pwa.mater", "version": "1.3.2", "oauth_type": "web",
              "language": "zh", "via": "pwa",
              "oauth_id": OAUTH_ID, "trace_id": OAUTH_ID,
              "playlet_id": playlet_id, "video_id": playlet_id,
              "episode_id": episode_id}
    params["sign"] = sign(params)
    req = urllib.request.Request(
        API, data=urllib.parse.urlencode(params).encode(),
        headers={"User-Agent": UA, "Referer": SITE,
                 "Origin": "https://again.agvibdto.cc",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.load(r)
    raw = base64.b64decode(j["data"].replace(" ", "+"))
    pt = _aes_cbc_decrypt(KEY, IV, raw)
    return json.loads(pt[:-pt[-1]].decode("utf-8"))


def sanitize(s: str) -> str:
    s = re.sub(r'[\/\\:*?"<>|]', "_", s).strip()
    return s or "drama"


def probe_video(path: str):
    """探测视频流参数。用 ffmpeg -i 解析（a-shell 不一定有 ffprobe）。
    返回 {'codec':, 'pix':, 'w':, 'h':, 'fps':, 'acodec':}，失败返回 None。"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    vinfo, acodec = None, ""
    for line in r.stderr.splitlines():
        if "Video:" in line and vinfo is None:
            c = re.search(r"Video:\s*(\w+)", line)
            p = re.search(r"Video:\s*\w+[^\n]*?,\s*([a-z0-9]+)\(", line)
            m = re.search(r"\b(\d{2,})x(\d{2,})\b", line)
            f = re.search(r"(\d+(?:\.\d+)?)\s*fps", line)
            if m:
                fps = f.group(1) if f else ""
                try:
                    fps = str(float(fps)) if fps else ""
                except ValueError:
                    pass
                vinfo = {"codec": c.group(1) if c else "",
                         "pix": p.group(1) if p else "",
                         "w": int(m.group(1)), "h": int(m.group(2)),
                         "fps": fps}
        elif "Audio:" in line and not acodec:
            a = re.search(r"Audio:\s*(\w+)", line)
            if a:
                acodec = a.group(1)
    if vinfo:
        vinfo["acodec"] = acodec
    return vinfo


def _transcode_cmd(ep_files, infos, out, venc, vargs):
    """转码合并命令：统一分辨率/fps。venc 如 h264_videotoolbox（手机硬件编码）。"""
    good = [i for i in infos if i]
    W = max([i["w"] for i in good]) if good else 720
    H = max([i["h"] for i in good]) if good else 1280
    fps_vals = [i["fps"] for i in good if i["fps"]]
    fps = max(set(fps_vals), key=fps_vals.count) if fps_vals else "30.0"
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    fc, cin = [], []
    for idx, f in enumerate(ep_files):
        cmd += ["-i", f]
        chain = []
        info = infos[idx]
        if not info or info["w"] != W or info["h"] != H:
            chain.append(f"scale={W}:{H}:flags=lanczos")
        if not info or info["fps"] != fps:
            chain.append(f"fps={fps}")
        chain.append("setsar=1")
        chain.append("format=yuv420p")
        fc.append(f"[{idx}:v]{','.join(chain)}[v{idx}]")
        cin.append(f"[v{idx}][{idx}:a]")
    fc.append("".join(cin) + f"concat=n={len(ep_files)}:v=1:a=1[v][a]")
    cmd += ["-filter_complex", ";".join(fc),
            "-map", "[v]", "-map", "[a]",
            "-c:v", venc] + vargs + ["-c:a", "aac", "-b:a", "128k", out]
    return cmd


def merge_eps(ep_files, out) -> bool:
    """智能合并：参数一致则无损快拼，否则统一转码（解决混分辨率导致的冻屏）。"""
    infos = [probe_video(f) for f in ep_files]
    if all(infos):
        keys = [(i["codec"], i["pix"], i["w"], i["h"], i["fps"], i["acodec"]) for i in infos]
        uniform = len(set(keys)) == 1
    else:
        uniform = False

    if uniform:
        print("分集参数一致，快速无损合并…", flush=True)
        lst = out + ".list.txt"
        with open(lst, "w") as f:
            for p in ep_files:
                f.write(f"file '{os.path.abspath(p)}'\n")
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-fflags", "+genpts",
                            "-f", "concat",
                            "-safe", "0", "-i", lst, "-c", "copy", out],
                           timeout=1800)
        os.remove(lst)
        return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0

    print("检测到分集画质不一致，转码统一合并（较慢，请稍候）…", flush=True)
    for venc, vargs in (("h264_videotoolbox", ["-b:v", "5M"]),
                        ("libx264", ["-preset", "veryfast", "-crf", "20"]),
                        ("mpeg4", ["-q:v", "3"])):
        print(f"尝试编码器 {venc}…", flush=True)
        cmd = _transcode_cmd(ep_files, infos, out, venc, vargs)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            return True
        print(f"{venc} 失败，报错：", flush=True)
        for line in (r.stderr or "").strip().splitlines()[-6:]:
            print(f"  {line}", flush=True)
    return False


def dl_ep(url: str, out: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner",
         "-headers", f"Referer: {SITE}\r\nUser-Agent: {UA}\r\n",
         "-i", url, "-c", "copy", out],
        timeout=3600)
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1024


def main():
    if len(sys.argv) < 2:
        print("用法: python3 yeguo_phone.py <短剧ID或详情页链接>")
        print("例:   python3 yeguo_phone.py 3282")
        return
    m = re.search(r"(\d+)", sys.argv[1])
    if not m:
        print("没找到短剧ID"); return
    pid = int(m.group(1))

    print("① 取全集地址…", flush=True)
    resp = api(pid)
    raw = resp.get("data")
    if isinstance(raw, list):
        if not raw:
            print(f"  接口返回空列表，msg={resp.get('msg')}", flush=True)
            return
        print(f"  接口返回列表结构，共 {len(raw)} 项", flush=True)
        if isinstance(raw[0], dict):
            print(f"  首项键: {list(raw[0].keys())}", flush=True)
        eps = raw
        title = f"drama_{pid}"
    elif isinstance(raw, dict):
        title = sanitize(raw.get("drama_name") or raw.get("video_title") or f"drama_{pid}")
        eps = raw.get("episodeAll") or []
    else:
        print(f"  接口返回未知结构: {type(raw).__name__}", flush=True)
        return
    if not eps:
        print("  没取到分集列表", flush=True)
        return
    print(f"《{title}》共 {len(eps)} 集", flush=True)

    os.makedirs(title, exist_ok=True)
    urls = {}
    for n, e in enumerate(eps, 1):
        if not isinstance(e, dict):
            continue
        url = e.get("video_url")
        if url:
            urls[e.get("index", n)] = url
    if not urls:
        print("  没解析到下载地址", flush=True)
        return

    failed = []
    for n in sorted(urls):
        out = os.path.join(title, f"ep{n:02d}.mp4")
        if os.path.exists(out) and os.path.getsize(out) > 1024:
            print(f"  ep{n:02d} 已存在，跳过", flush=True); continue
        print(f"② 下载 ep{n:02d}/{len(urls)} …", flush=True)
        if not dl_ep(urls[n], out):
            print("   失败，重新取地址再试一次…", flush=True)
            try:
                urls = {e["index"]: e["video_url"]
                        for e in api(pid)["data"]["episodeAll"]}
                ok = dl_ep(urls[n], out)
            except Exception as ex:
                ok = False
                print(f"   重试异常: {ex}", flush=True)
            if not ok:
                failed.append(n)
                print(f"   ep{n:02d} 失败，先继续下一集", flush=True)
    if failed:
        print(f"有 {len(failed)} 集没下完：{failed}")
        print("网络恢复后重跑本脚本会自动续下，暂不合并")
        return

    print("③ 合并…", flush=True)
    ep_files = [os.path.join(title, f"ep{n:02d}.mp4") for n in sorted(urls)]
    merged = f"{title}.mp4"
    if merge_eps(ep_files, merged):
        mb = os.path.getsize(merged) // 1048576
        print(f"④ 完成：{merged}（{mb}MB），清理分集…", flush=True)
        for p in ep_files:
            os.remove(p)
        os.rmdir(title)
        print("搞定，直接看吧")
    else:
        print("合并失败，分集保留在文件夹里")


if __name__ == "__main__":
    main()
