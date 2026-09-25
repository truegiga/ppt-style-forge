#!/usr/bin/env python3
"""PPT 模板风格采集器 — 三合一 CLI

用法：
  python ppt_harvest.py links  <首页HTML> <输出txt>          # 从站点HTML提 pptx 下载直链
  python ppt_harvest.py fetch  <链接txt> <输出目录>          # 并发下载 pptx
  python ppt_harvest.py parse  <pptx目录> <输出json>         # 解析主题色/字体/字号/布局指纹
  python ppt_harvest.py palette <预览图目录> <输出json>       # 预览图主色板量化
  python ppt_harvest.py layout <pptx目录> <输出json>         # 布局节奏体检（治「模式单一」）
      逐页算: 骨架多样性 / 邻页重复率 / 单骨架占比 / 密度变异系数 / 重心游走
      达标线: 单骨架<=0.25  邻页重复<=0.10  密度变异系数>=0.70  重心游走>=0.20
      （基线: 真人模板中位 0.19 / 0.00 / 0.81 / 0.27；WorkBuddy 自产 0.47 / 0.31 / 0.42 / 0.14）

依赖：Python 3.11+（已装 Pillow 时 palette 可用）
"""
import sys, re, json, pathlib, collections, statistics, zipfile
import concurrent.futures as cf
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/120 Safari/537.36")

# ---------- ① 提下载链接 ----------
def cmd_links(html_path, out_txt):
    html = pathlib.Path(html_path).read_text(encoding="utf8", errors="ignore")
    links = sorted(set(re.findall(
        r'https://www\.slidescarnival\.com/download/sc\d+/[a-z0-9-]+/pptx', html)))
    pathlib.Path(out_txt).write_text("\n".join(links))
    print(f"提到 {len(links)} 条下载直链 → {out_txt}")

# ---------- ② 并发下载 ----------
def cmd_fetch(txt, outdir):
    links = [l.strip() for l in pathlib.Path(txt).read_text().splitlines() if l.strip()]
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)

    def one(u):
        slug = u.rstrip("/").split("/")[-2]
        p = out / f"{slug}.pptx"
        if p.exists() and p.stat().st_size > 20000:
            return f"skip {slug}"
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": UA, "Referer": "https://www.slidescarnival.com/"})
            d = urllib.request.urlopen(req, timeout=120).read()
            p.write_bytes(d)
            return f"OK {slug} {len(d)//1024}KB"
        except Exception as e:
            return f"FAIL {slug} {e}"

    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(one, links):
            print(r, flush=True)
    print("DONE", len(list(out.glob("*.pptx"))))

# ---------- ③ 解析 pptx ----------
def _theme(z):
    try:
        x = z.read("ppt/theme/theme1.xml").decode("utf8", "ignore")
    except KeyError:
        return {}, {}
    colors = {}
    m = re.search(r"<a:clrScheme.*?</a:clrScheme>", x, re.S)
    if m:
        for name, sysv, srgb in re.findall(
                r'<a:(\w+)[^>]*>\s*<a:(?:sysClr val="[^"]+" (?:lastClr="([0-9A-Fa-f]{6})")?|srgbClr val="([0-9A-Fa-f]{6})")',
                m.group(0)):
            hexv = sysv or srgb
            if hexv:
                colors[name] = "#" + hexv.upper()
    fonts = {}
    m = re.search(r"<a:fontScheme.*?</a:fontScheme>", x, re.S)
    if m:
        for tag in ("majorFont", "minorFont"):
            t = re.search(rf"<a:{tag}>(.*?)</a:{tag}>", m.group(0), re.S)
            if t:
                fonts[tag] = dict(re.findall(r'<a:(\w+) typeface="([^"]+)"', t.group(1)))
    return colors, fonts

def _canvas(z):
    try:
        x = z.read("ppt/presentation.xml").decode("utf8", "ignore")
        m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', x)
        if m:
            return int(m.group(1)), int(m.group(2))
    except KeyError:
        pass
    return 12192000, 6858000  # 16:9 默认

def _sig(boxes):
    """3x3 网格占据指纹 → 9 位串，用于判「布局变体」"""
    grid = [[0]*3 for _ in range(3)]
    for x, y, w, h in boxes:
        for r in range(3):
            for c in range(3):
                gx, gy = (c+0.5)/3, (r+0.5)/3
                if x <= gx <= x+w and y <= gy <= y+h:
                    grid[r][c] = 1
    return "".join(str(v) for row in grid for v in row)

def cmd_parse(dirpath, out_json):
    res = []
    for p in sorted(pathlib.Path(dirpath).glob("*.pptx")):
        try:
            z = zipfile.ZipFile(p)
            slides = sorted([n for n in z.namelist()
                             if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                            key=lambda n: int(re.findall(r"\d+", n)[0]))
            tc, tf = _theme(z)
            cw, ch = _canvas(z)
            colors, sizes, sigs, shapes, chars = (collections.Counter(),
                                                  collections.Counter(), [], [], 0)
            for s in slides:
                x = z.read(s).decode("utf8", "ignore")
                shapes.append(len(re.findall(r"<p:sp>|<p:pic>|<p:graphicFrame>", x)))
                colors.update(re.findall(r'<a:solidFill><a:srgbClr val="([0-9A-Fa-f]{6})"', x))
                sizes.update(int(v) for v in re.findall(r'sz="(\d+)"', x))
                boxes = [(int(a)/cw, int(b)/ch, int(c)/cw, int(d)/ch)
                         for a, b, c, d in re.findall(
                             r'<a:off x="(-?\d+)" y="(-?\d+)"[^>]*/>\s*<a:ext cx="(\d+)" cy="(\d+)"', x)
                         if int(c) > 0 and int(d) > 0]
                sigs.append(_sig(boxes))
                chars += len("".join(re.findall(r"<a:t>(.*?)</a:t>", x, re.S)))
            res.append({
                "file": p.name, "n_slides": len(slides),
                "theme_colors": tc, "theme_fonts": tf,
                "top_colors": [("#"+c.upper(), n) for c, n in colors.most_common(8)],
                "top_sizes": [(s/100, n) for s, n in sizes.most_common(10)],
                "layouts": sigs, "avg_shapes": round(statistics.mean(shapes), 1) if shapes else 0,
                "unique_layouts": len(set(sigs)), "chars": chars,
            })
        except Exception as e:
            print("ERR", p.name, e)
    pathlib.Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res:
        print(f"{r['file'][:34]:<36} 页{r['n_slides']:<3} 形{r['avg_shapes']:<5} "
              f"布局变体{r['unique_layouts']:<3} 字符{r['chars']}")

# ---------- ④ 预览图色板 ----------
def cmd_palette(dirpath, out_json, n=6):
    from PIL import Image
    res = []
    for p in sorted(pathlib.Path(dirpath).glob("*.jpg")) + \
             sorted(pathlib.Path(dirpath).glob("*.png")):
        img = Image.open(p).convert("RGB").resize((160, 90))
        q = img.quantize(colors=n)
        pal, cnt, total = q.getpalette(), collections.Counter(q.getdata()), 0
        total = sum(cnt.values())
        board = []
        for idx, c in cnt.most_common(n):
            r, g, b = pal[idx*3: idx*3+3]
            board.append((f"#{r:02X}{g:02X}{b:02X}", round(c/total*100, 1)))
        res.append({"slug": p.stem, "palette": board})
        print(f"{p.stem[:38]:<40} " + " ".join(f"{h}({pc}%)" for h, pc in board[:5]))
    pathlib.Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1))

# ---------- ⑤ 布局节奏体检 ----------
# 关键：必须先剔除背景/蒙版层（面积>55%页面的形状），否则所有页都是"铺满"，
# 指纹全是 111111，区分度为零。踩过。
GW, GH = 6, 4


def _canvas_emu(z):
    """返回画布宽高（EMU）"""
    try:
        x = z.read("ppt/presentation.xml").decode("utf8", "ignore")
        m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', x)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 12192000, 6858000


def _fg_boxes(z, name, W, H):
    """取前景块（剔除面积>55%页面的背景层）"""
    x = z.read(name).decode("utf8", "ignore")
    bs = []
    for ox, oy, cx, cy in re.findall(
            r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>', x):
        ox, oy, cx, cy = map(int, (ox, oy, cx, cy))
        if cx > 0 and cy > 0:
            bs.append((ox, oy, cx, cy))
    area = W * H
    fg = [b for b in bs if b[2] * b[3] < 0.55 * area] or bs
    return fg, x


def _fp(boxes, W, H):
    grid = [[0] * GW for _ in range(GH)]
    for ox, oy, cx, cy in boxes:
        x0, x1 = ox / W, (ox + cx) / W
        y0, y1 = oy / H, (oy + cy) / H
        for gy in range(GH):
            for gx in range(GW):
                ow = max(0, min(x1, (gx + 1) / GW) - max(x0, gx / GW))
                oh = max(0, min(y1, (gy + 1) / GH) - max(y0, gy / GH))
                if ow * oh > 0.10 / (GW * GH):
                    grid[gy][gx] += 1
    return "".join("1" if c else "0" for r in grid for c in r)


def cmd_layout(dirpath, out_json):
    res = []
    for p in sorted(pathlib.Path(dirpath).glob("*.pptx")):
        try:
            z = zipfile.ZipFile(p)
            W, H = _canvas_emu(z)
            names = sorted([n for n in z.namelist()
                            if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                           key=lambda n: int(re.findall(r"\d+", n)[0]))
            pages = []
            for s in names:
                fg, raw = _fg_boxes(z, s, W, H)
                if not fg:
                    continue
                pages.append({
                    "fp": _fp(fg, W, H), "n_fg": len(fg),
                    "cx": round(sum(b[0] + b[2] / 2 for b in fg) / len(fg) / W, 2),
                    "cy": round(sum(b[1] + b[3] / 2 for b in fg) / len(fg) / H, 2),
                    "n_para": len(re.findall(r"<a:p>", raw)),
                })
            if len(pages) < 2:
                continue
            fps = [q["fp"] for q in pages]
            n = len(fps)
            fg_n = [q["n_fg"] for q in pages]
            rep = sum(1 for i in range(1, n) if fps[i] == fps[i - 1]) / (n - 1)
            top = collections.Counter(fps).most_common(1)[0][1] / n
            mean = statistics.mean(fg_n)
            cv = statistics.pstdev(fg_n) / mean if mean else 0
            mv = statistics.median([
                ((pages[i]["cx"] - pages[i - 1]["cx"]) ** 2 +
                 (pages[i]["cy"] - pages[i - 1]["cy"]) ** 2) ** 0.5
                for i in range(1, n)])
            center = sum(1 for q in pages
                         if 0.45 <= q["cx"] <= 0.55 and 0.45 <= q["cy"] <= 0.55) / n
            sparse = sum(1 for v in fg_n if v <= 10) / n
            st = {"pages": n, "uniq_ratio": round(len(set(fps)) / n, 2),
                  "adj_rep": round(rep, 2), "top_fp_share": round(top, 2),
                  "density_cv": round(cv, 2), "focus_move": round(mv, 2),
                  "center_share": round(center, 2), "sparse_share": round(sparse, 2)}
            res.append({"name": p.stem, "stat": st, "pages": pages})
            ok = (st["top_fp_share"] <= 0.25 and st["adj_rep"] <= 0.10
                  and st["density_cv"] >= 0.70 and st["focus_move"] >= 0.20)
            print(f"{p.stem[:32]:<34} 页{n:>3} 单骨架{st['top_fp_share']:.2f} "
                  f"邻重{st['adj_rep']:.2f} 密度CV{st['density_cv']:.2f} "
                  f"重心游走{st['focus_move']:.2f} 居中{st['center_share']:.2f} "
                  f"稀疏{st['sparse_share']:.2f}  {'✅' if ok else '❌'}")
        except Exception as e:
            print("ERR", p.name, e)
    pathlib.Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    if res:
        def med(k):
            return statistics.median([r["stat"][k] for r in res])
        print(f"\n中位: 单骨架{med('top_fp_share')} 邻重{med('adj_rep')} "
              f"密度CV{med('density_cv')} 重心游走{med('focus_move')} "
              f"居中{med('center_share')} 稀疏{med('sparse_share')}")
        print("达标线: 单骨架<=0.25 邻重<=0.10 密度CV>=0.70 重心游走>=0.20")
    print("→", out_json)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    cmd, args = a[0], a[1:]
    {"links": cmd_links, "fetch": cmd_fetch,
     "parse": cmd_parse, "palette": cmd_palette,
     "layout": cmd_layout}[cmd](*args)
