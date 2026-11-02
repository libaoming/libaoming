"""Render a GitHub profile card from public account data and its real avatar."""
from __future__ import annotations

import io
import json
import math
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
USER = "libaoming"


def fetch(url: str, api: bool = False) -> bytes:
    headers = {"User-Agent": "libaoming-profile"}
    if api and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return response.read()


def public_data():
    if os.environ.get("PROFILE_OFFLINE") == "1":
        profile = json.loads((ROOT / "profile.json").read_text())
        repos = [repo for page in json.loads((ROOT / "repos-pages.json").read_text()) for repo in page]
        avatar = (ROOT / "avatar.png").read_bytes()
    else:
        profile = json.loads(fetch(f"https://api.github.com/users/{USER}", True))
        repos = []
        page = 1
        while True:
            batch = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}", True))
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        avatar = fetch(profile["avatar_url"])
    return profile, repos, avatar


def ascii_portrait(data: bytes) -> list[str]:
    # Sampling the actual avatar; no generated or substituted face.
    im = Image.open(io.BytesIO(data)).convert("L")
    im = ImageOps.fit(im, (440, 440), method=Image.Resampling.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    im = im.resize((44, 34), Image.Resampling.LANCZOS)
    ramp = "@%#*+=-:. "
    lines = []
    for y in range(im.height):
        line = ""
        for x in range(im.width):
            # Match the circular crop on the real GitHub avatar.
            distance = ((x + .5 - 22) / 22) ** 2 + ((y + .5 - 17) / 17) ** 2
            line += " " if distance > 1 else ramp[min(9, im.getpixel((x, y)) * 10 // 256)]
        lines.append(line.rstrip())
    return lines


def card(profile, repos, portrait, dark: bool) -> str:
    c = dict(bg="#0d1117", border="#30363d", text="#c9d1d9", muted="#6e7681", art="#b1bac4", blue="#58a6ff", label="#ffa657") if dark else dict(bg="#ffffff", border="#d0d7de", text="#24292f", muted="#afb8c1", art="#57606a", blue="#0969da", label="#953800")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="580" viewBox="0 0 960 580" role="img" aria-labelledby="title desc">',
           '<title id="title">libaoming — GitHub profile</title>',
           '<desc id="desc">ASCII portrait generated from libaoming’s GitHub avatar, account information and public repository statistics.</desc>',
           '<style>text{font-family:Consolas,"Liberation Mono",Menlo,monospace;font-size:13px}</style>',
           f'<rect x=".5" y=".5" width="959" height="579" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>']

    def text(x, y, value, color="text", size=None):
        style = f' style="font-size:{size}px"' if size else ""
        return f'<text x="{x}" y="{y}" fill="{c[color]}" xml:space="preserve"{style}>{escape(str(value))}</text>'

    for i, line in enumerate(portrait):
        out.append(text(22, 49 + i * 14.4, line, "art", 13))

    def section(y, title):
        out.append(text(405, y, title, "blue"))
        start = 405 + len(title) * 7.8 + 12
        out.append(f'<path d="M{start} {y - 4}H932" stroke="{c["muted"]}"/>')

    def row(y, label, value, link=None):
        value = str(value)
        out.append(text(405, y, label + ":", "label"))
        start = 405 + (len(label) + 2) * 7.8
        end = 932 - (len(value) + 1) * 7.8
        if end > start:
            out.append(f'<path d="M{start} {y - 2}H{end}" stroke="{c["muted"]}" stroke-width="2" stroke-dasharray="2 5"/>')
        content = f'<text x="932" y="{y}" text-anchor="end" fill="{c["text"]}" xml:space="preserve">{escape(value)}</text>'
        out.append(f'<a href="{escape(link, quote=True)}">{content}</a>' if link else content)

    section(48, USER + "@github")
    row(91, "OS", "macOS")
    row(115, "Focus", "AI agents & tooling")
    row(139, "Location", "Beijing, China")
    row(163, "GitHub since", profile["created_at"][:10])
    row(187, "Tools", "Claude Code, Codex")
    row(235, "Languages", "Python, TypeScript, Shell")
    row(259, "Interests", "Agent design, Skills, Evals")
    section(310, "─ Contact")
    row(337, "GitHub", "github.com/libaoming", "https://github.com/libaoming")
    row(361, "WeChat", "dereckie")
    section(414, "─ GitHub Stats")
    originals = [r for r in repos if not r["fork"]]
    row(441, "Public repos", profile["public_repos"])
    row(465, "Original repos", len(originals))
    row(489, "Stars on original repos", sum(r["stargazers_count"] for r in originals))
    row(513, "Followers", profile["followers"])
    row(537, "Following", profile["following"])
    out.append(text(405, 563, "Updated " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + " · public GitHub data", "muted", 10))
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    profile, repos, avatar = public_data()
    portrait = ascii_portrait(avatar)
    for mode in ["light", "dark"]:
        (ROOT / f"{mode}_mode.svg").write_text(card(profile, repos, portrait, mode == "dark"))
    (ROOT / "portrait.txt").write_text("\n".join(portrait) + "\n")
    print(f"Rendered actual avatar and {len(repos)} public repositories.")
