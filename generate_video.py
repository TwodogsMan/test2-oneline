"""
Self-introduction video generator.
Generates a ~75 second self-introduction video using Pillow + OpenCV.
Output: self_intro.avi (MJPG codec, 1280x720, 30fps)
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import os

# ============================================================
# CONFIGURATION
# ============================================================
W, H = 1280, 720
FPS = 30
TOTAL_FRAMES = FPS * 75  # 2250 frames = 75 seconds

# Scene boundaries: (start_frame, end_frame)
SCENES = [
    (0,     240),   # 0-8s    Opening
    (240,   660),   # 8-22s   About Me
    (660,   1260),  # 22-42s  Skills
    (1260,  1800),  # 42-60s  Experience
    (1800,  2250),  # 60-75s  Closing
]

# Colors (RGB for Pillow)
C_BG       = (15, 23, 42)
C_CARD     = (30, 41, 59)
C_ACCENT   = (56, 189, 248)
C_ACCENT2  = (129, 140, 248)
C_TEXT     = (226, 232, 240)
C_MUTED    = (148, 163, 184)
C_BLACK    = (0, 0, 0)
C_BAR_BG   = (40, 50, 70)

FADE = 15  # frames for fade in/out at scene boundaries

# ============================================================
# FONTS
# ============================================================
FONT_FILE      = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD_FILE = 'C:/Windows/Fonts/msyhbd.ttc'

fonts: dict = {}

def init_fonts():
    """Load all needed font sizes."""
    sizes = {
        'hero':   80,
        'title':  56,
        'head':   40,
        'sub':    32,
        'body':   28,
        'small':  20,
        'tag':    18,
    }
    for name, size in sizes.items():
        try:
            fonts[name] = ImageFont.truetype(FONT_BOLD_FILE if name in ('hero','title','head') else FONT_FILE, size)
        except Exception:
            fonts[name] = ImageFont.load_default()
            print(f"Warning: fallback font for {name}")

# ============================================================
# EASING FUNCTIONS
# ============================================================
def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def ease_out(t):
    """Cubic ease-out."""
    t = clamp(t)
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    """Cubic ease-in-out."""
    t = clamp(t)
    return 4*t*t*t if t < 0.5 else 1 - (-2*t + 2)**3 / 2

def ease_out_back(t):
    """Ease-out-back: slight overshoot for pop effect."""
    t = clamp(t)
    c1 = 1.70158
    return 1 + (c1 + 1) * (t - 1)**3 + c1 * (t - 1)**2

def anim_progress(local_frame, start, duration):
    """Return 0.0-1.0 animation progress. Returns 0 before start, eases to 1 at start+duration."""
    if local_frame < start:
        return 0.0
    if local_frame >= start + duration:
        return 1.0
    t = (local_frame - start) / duration
    return ease_out(t)

def fade_progress(local_frame, start, duration):
    """Linear fade progress for alpha blending."""
    if local_frame < start:
        return 0.0
    if local_frame >= start + duration:
        return 1.0
    return (local_frame - start) / duration

# ============================================================
# DRAWING HELPERS
# ============================================================
def gradient_bg(w, h, top, bottom):
    """Vertical gradient via numpy (fast)."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = np.linspace(top[i], bottom[i], h, dtype=np.uint8)[:, np.newaxis]
    return Image.fromarray(arr, 'RGB')

def tw(draw, text, font):
    """Text width."""
    return draw.textlength(text, font=font)

def draw_t(draw, x, y, text, font, color):
    """Draw text at (x, y), top-left anchor."""
    draw.text((x, y), text, font=font, fill=color)

def draw_tc(draw, y, text, font, color):
    """Draw horizontally centered text."""
    w = tw(draw, text, font)
    draw.text(((W - w) // 2, y), text, font=font, fill=color)

def draw_card(draw, x, y, w, h, r=12, fill=C_CARD):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)

def draw_bar(draw, x, y, w, h, progress, color, bg=C_BAR_BG):
    """Rounded progress bar. progress: 0.0 ~ 1.0."""
    r = h // 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=bg)
    if progress > 0.005:
        fw = max(r * 2, int(w * clamp(progress)))
        draw.rounded_rectangle([x, y, x + fw, y + h], radius=r, fill=color)

def draw_tag(draw, x, y, text, font, tc=C_ACCENT, bg=None):
    """Pill-shaped tag."""
    if bg is None:
        bg = (30, 60, 80)
    bw, bh = tw(draw, text, font), font.size + 12
    px, py = 14, 6
    draw.rounded_rectangle([x, y, x + bw + px*2, y + bh + py*2], radius=(bh+py*2)//2, fill=bg)
    draw.text((x + px, y + py), text, font=font, fill=tc)

def lerp_color(c1, c2, t):
    """Linear interpolate two RGB colors."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * clamp(t)) for i in range(3))

# ============================================================
# SCENE 1: OPENING (0-8s, 240 frames)
# ============================================================
def render_opening(f, dur):
    """Name reveal + subtitle + tags."""
    img = gradient_bg(W, H, (8, 12, 30), C_BG)
    draw = ImageDraw.Draw(img)

    # Decorative circles (static)
    for cx, cy, r, a in [(200, 150, 120, 0.04), (1080, 550, 180, 0.06), (150, 580, 90, 0.05)]:
        overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*C_ACCENT, int(255*a)), outline=None)
        img.paste(overlay, (0, 0), overlay)

    # Horizontal accent line (expands from center)
    lp = anim_progress(f, 30, 60)
    line_w = int(280 * lp)
    if line_w > 0:
        ly = 380
        draw.line([(W//2 - line_w, ly), (W//2 + line_w, ly)], fill=C_ACCENT, width=3)

    # Name: typewriter effect
    name = "张三"
    typed = min(len(name), max(0, int((f - 10) / 22) + 1)) if f >= 10 else 0
    show_text = name[:typed]
    if show_text:
        ft = fonts['hero']
        # Center the full text, but for partial text, measure what's shown
        full_w = tw(draw, name, ft)
        shown_w = tw(draw, show_text, ft) if show_text else 0
        # Position so the full name ends up centered, but we draw from the left of the full name
        base_x = (W - full_w) // 2
        draw_t(draw, base_x, 280, show_text, ft, C_TEXT)

    # Cursor blink
    if typed < len(name) and (f // 15) % 2 == 0 and f >= 10:
        full_w2 = tw(draw, name, fonts['hero'])
        base_x2 = (W - full_w2) // 2
        cursor_x = base_x2 + tw(draw, show_text, fonts['hero']) + 8
        draw_t(draw, cursor_x, 280, "|", fonts['hero'], C_ACCENT)

    # Subtitle (fade in)
    sp = fade_progress(f, 75, 50)
    if sp > 0:
        subtitle = "全栈开发工程师 · 开源爱好者 · 终身学习者"
        sc = lerp_color(C_BG, C_MUTED, sp)
        draw_tc(draw, 410, subtitle, fonts['sub'], sc)

    # Skill tags (pop in, staggered)
    tags = ["⚛ React", "🐍 Python", "🟢 Node.js", "🤖 AI"]
    for i, tag in enumerate(tags):
        tp = anim_progress(f, 150 + i*15, 35)
        if tp > 0:
            scale = 1.0 + (1 - tp) * 0.5  # pop from 1.5x to 1.0x
            tag_w = tw(draw, tag, fonts['tag'])
            # Compute position for centered 4 tags
            total_w = sum(tw(draw, t, fonts['tag']) for t in tags) + 15 * 3  # 3 gaps
            start_x = (W - total_w) // 2
            offset_x = 0
            for j in range(i):
                offset_x += tw(draw, tags[j], fonts['tag']) + 15
            tx = start_x + offset_x
            ty = 480
            draw_tag(draw, tx, ty, tag, fonts['tag'])

    # Fade overlay
    return apply_fade(img, f, dur)

# ============================================================
# SCENE 2: ABOUT ME (8-22s, 420 frames)
# ============================================================
def render_about(f, dur):
    img = gradient_bg(W, H, (10, 15, 35), C_BG)
    draw = ImageDraw.Draw(img)

    # Title
    tp = anim_progress(f, 0, 20)
    tc = lerp_color(C_BG, C_TEXT, tp)
    draw_tc(draw, 55, "📋  关于我", fonts['title'], tc)
    # Underline
    if tp > 0.5:
        ul_w = int(100 * ease_out(clamp((tp - 0.5) * 2)))
        draw.line([(W//2 - ul_w, 130), (W//2 + ul_w, 130)], fill=C_ACCENT, width=3)

    # Paragraphs (slide in from left)
    paragraphs = [
        "我是一名拥有 6 年经验的全栈开发工程师，目前居住在上海。",
        "热衷于使用现代 Web 技术构建优雅、高性能的应用程序。",
        "注重代码质量、测试覆盖率和用户体验，是开源社区的活跃贡献者。",
    ]
    for pi, para in enumerate(paragraphs):
        pp = anim_progress(f, 25 + pi*30, 40)
        offset = int((1 - pp) * 80)
        pc = lerp_color(C_BG, C_MUTED, pp)
        draw_t(draw, 120 + offset, 165 + pi*48, para, fonts['body'], pc)

    # Info cards (2x2 grid, pop-in)
    cards_info = [
        ("📍 所在地", "中国 · 上海"),
        ("💼 当前职位", "高级前端工程师"),
        ("🎓 学历", "计算机科学 硕士"),
        ("📧 邮箱", "zhangsan@example.com"),
    ]
    card_w, card_h = 240, 100
    grid_start_x = 140
    grid_start_y = 350
    gap_x, gap_y = 30, 20

    for i, (label, value) in enumerate(cards_info):
        col, row = i % 2, i // 2
        cx = grid_start_x + col * (card_w + gap_x)
        cy = grid_start_y + row * (card_h + gap_y)
        cp = anim_progress(f, 160 + i*35, 35)

        if cp > 0:
            # Pop-in with slight scale
            sc = 1.0 + (1 - cp) * 0.4
            pw, ph = int(card_w * sc), int(card_h * sc)
            px = cx - (pw - card_w) // 2
            py = cy - (ph - card_h) // 2

            # Card background with alpha
            alpha = int(255 * clamp(cp * 1.2))
            overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rounded_rectangle([px, py, px+pw, py+ph], radius=12,
                                 fill=(*C_CARD, alpha))
            img.paste(overlay, (0, 0), overlay)

            if cp > 0.3:
                # Re-draw for text
                draw2 = ImageDraw.Draw(img)
                draw_t(draw2, cx + 20, cy + 18, label, fonts['small'], C_MUTED)
                draw_t(draw2, cx + 20, cy + 48, value, fonts['body'], C_ACCENT)

    return apply_fade(img, f, dur)

# ============================================================
# SCENE 3: SKILLS (22-42s, 600 frames)
# ============================================================
def render_skills(f, dur):
    img = gradient_bg(W, H, (10, 15, 35), C_BG)
    draw = ImageDraw.Draw(img)

    # Title
    tp = anim_progress(f, 0, 20)
    draw_tc(draw, 50, "🛠  专业技能", fonts['title'], lerp_color(C_BG, C_TEXT, tp))
    if tp > 0.5:
        ul_w = int(100 * ease_out(clamp((tp-0.5)*2)))
        draw.line([(W//2 - ul_w, 120), (W//2 + ul_w, 120)], fill=C_ACCENT, width=3)

    # Skill rows
    skills = [
        ("🎨 前端开发", 0.95, ["React", "Vue", "TypeScript", "Next.js", "Tailwind CSS"]),
        ("⚙️ 后端开发", 0.85, ["Node.js", "Python", "Go", "PostgreSQL", "Redis"]),
        ("☁️ DevOps & 云", 0.72, ["Docker", "Kubernetes", "AWS", "CI/CD", "Terraform"]),
        ("🤖 AI & 数据", 0.78, ["LangChain", "RAG", "Pandas", "Agent", "Vector DB"]),
    ]

    row_y = 170
    row_h = 120
    bar_w = 500
    bar_h = 18
    tag_start_x = 180

    for i, (label, target_pct, tags) in enumerate(skills):
        ry = row_y + i * row_h
        rp = anim_progress(f, 20 + i*65, 60)

        if rp > 0:
            # Label
            lc = lerp_color(C_BG, C_TEXT, clamp(rp * 1.5))
            draw_t(draw, 100, ry + 10, label, fonts['head'], lc)

            # Progress bar background (animated)
            bp = anim_progress(f, 50 + i*65, 80)  # bar fill starts after label
            bar_fill = bp * target_pct
            draw_bar(draw, 100, ry + 60, bar_w, bar_h, bar_fill, C_ACCENT)

            # Percentage text
            if bp > 0.1:
                pct_text = f"{int(bar_fill * 100)}%"
                draw_t(draw, 100 + bar_w + 20, ry + 55, pct_text, fonts['sub'], C_ACCENT)

            # Tags
            tp_tag = anim_progress(f, 70 + i*65, 60)
            if tp_tag > 0:
                tag_x = tag_start_x
                for tag in tags:
                    tc2 = lerp_color(C_BG, C_ACCENT, clamp(tp_tag * 1.3))
                    draw_tag(draw, tag_x, ry + 90, tag, fonts['tag'], tc=tc2)
                    tag_x += tw(draw, tag, fonts['tag']) + 26

    return apply_fade(img, f, dur)

# ============================================================
# SCENE 4: EXPERIENCE (42-60s, 540 frames)
# ============================================================
def render_experience(f, dur):
    img = gradient_bg(W, H, (10, 15, 35), C_BG)
    draw = ImageDraw.Draw(img)

    # Title
    tp = anim_progress(f, 0, 20)
    draw_tc(draw, 50, "💼  工作经历", fonts['title'], lerp_color(C_BG, C_TEXT, tp))
    if tp > 0.5:
        ul_w = int(100 * ease_out(clamp((tp-0.5)*2)))
        draw.line([(W//2 - ul_w, 120), (W//2 + ul_w, 120)], fill=C_ACCENT, width=3)

    # Timeline line
    timeline_x = 180
    line_p = anim_progress(f, 20, 450)
    line_h = int(420 * line_p)
    if line_h > 0:
        draw.line([(timeline_x, 160), (timeline_x, 160 + line_h)], fill=C_ACCENT, width=2)

    # Job entries
    jobs = [
        ("2023.03 — 至今", "高级前端工程师", "ABC 科技有限公司 · 上海",
         "主导核心产品前端架构重构，搭建组件库和设计系统，引入 E2E 测试体系。"),
        ("2020.07 — 2023.02", "全栈开发工程师", "XYZ 互联网公司 · 杭州",
         "负责电商平台订单系统和支付模块，日处理订单量 10W+。"),
        ("2018.09 — 2020.06", "初级前端开发", "DEF 创业公司 · 北京",
         "参与核心产品从零开发，帮助公司在一年内获得 10 万用户。"),
    ]

    for i, (date, title, org, desc) in enumerate(jobs):
        jp = anim_progress(f, 30 + i*120, 80)

        if jp > 0:
            jy = 170 + i * 150
            slide = int((1 - jp) * 100)

            # Timeline dot
            dot_alpha = clamp(jp * 2)
            dot_r = 8
            overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([timeline_x - dot_r, jy + 5 - dot_r, timeline_x + dot_r, jy + 5 + dot_r],
                       fill=(*C_ACCENT, int(255 * dot_alpha)))
            img.paste(overlay, (0, 0), overlay)

            # Content
            draw2 = ImageDraw.Draw(img)
            cx = timeline_x + 50 + slide
            # Date
            draw_t(draw2, cx, jy - 8, date, fonts['small'],
                   lerp_color(C_BG, C_ACCENT, jp))
            # Title
            draw_t(draw2, cx, jy + 18, title, fonts['head'],
                   lerp_color(C_BG, C_TEXT, clamp(jp * 1.3)))
            # Org
            draw_t(draw2, cx, jy + 60, org, fonts['small'],
                   lerp_color(C_BG, C_MUTED, clamp(jp * 1.4)))
            # Description
            draw_t(draw2, cx, jy + 90, desc, fonts['body'],
                   lerp_color(C_BG, C_MUTED, clamp(jp * 1.5)))

    return apply_fade(img, f, dur)

# ============================================================
# SCENE 5: CLOSING (60-75s, 450 frames)
# ============================================================
def render_closing(f, dur):
    img = gradient_bg(W, H, C_BG, (8, 12, 30))
    draw = ImageDraw.Draw(img)

    # Decorative circle
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([W//2 - 200, 60, W//2 + 200, 460], fill=(*C_ACCENT, 15), outline=None)
    img.paste(overlay, (0, 0), overlay)

    # "感谢观看" - scale up
    tp = anim_progress(f, 10, 50)
    if tp > 0:
        sc = 0.5 + tp * 0.5
        txt = "感谢观看"
        ft = fonts['hero']
        txt_w, txt_h = tw(draw, txt, ft), ft.size + 10
        # Scale by rendering on a temp image
        scaled_w = int(txt_w * sc)
        scaled_h = int(txt_h * sc)
        # Actually, PIL can't scale text directly. Use scale as alpha proxy + size feel
        # Simpler: just fade in
        tc = lerp_color(C_BG, C_TEXT, tp)
        draw_tc(draw, 180, txt, fonts['hero'], tc)

    # Decorative line under "感谢观看"
    lp = anim_progress(f, 40, 40)
    if lp > 0:
        line_w2 = int(200 * lp)
        draw.line([(W//2 - line_w2, 280), (W//2 + line_w2, 280)], fill=C_ACCENT, width=2)

    # Subtitle
    sp = anim_progress(f, 60, 40)
    draw_tc(draw, 320, "期待与您合作！", fonts['sub'], lerp_color(C_BG, C_MUTED, sp))

    # Contact cards (fade in grid)
    contacts = [
        ("📧", "Email", "zhangsan@example.com"),
        ("🐙", "GitHub", "@zhangsan"),
        ("💬", "微信", "zhangsan_wx"),
        ("🔗", "LinkedIn", "@zhangsan"),
    ]
    card_w2, card_h2 = 220, 140
    total_cards_w = len(contacts) * card_w2 + (len(contacts) - 1) * 20
    start_cx = (W - total_cards_w) // 2

    for i, (icon, label, value) in enumerate(contacts):
        cp = anim_progress(f, 100 + i*30, 45)
        if cp > 0:
            cx2 = start_cx + i * (card_w2 + 20)
            cy2 = 370
            # Pop
            sc2 = 1.0 + (1 - cp) * 0.3
            pw2, ph2 = int(card_w2 * sc2), int(card_h2 * sc2)
            px2 = cx2 - (pw2 - card_w2) // 2
            py2 = cy2 - (ph2 - card_h2) // 2

            ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            od2 = ImageDraw.Draw(ov)
            od2.rounded_rectangle([px2, py2, px2+pw2, py2+ph2], radius=16,
                                  fill=(*C_CARD, int(255*clamp(cp*1.3))))
            img.paste(ov, (0, 0), ov)

            if cp > 0.35:
                draw3 = ImageDraw.Draw(img)
                draw_tc_ctx(draw3, cx2, cy2+8, card_w2, icon, fonts['head'],
                           lerp_color(C_BG, C_TEXT, clamp((cp-0.35)*1.5)))
                draw_tc_ctx(draw3, cx2, cy2+62, card_w2, label, fonts['small'],
                           lerp_color(C_BG, C_MUTED, clamp((cp-0.35)*2)))
                draw_tc_ctx(draw3, cx2, cy2+90, card_w2, value, fonts['small'],
                           lerp_color(C_BG, C_ACCENT, clamp((cp-0.35)*2.5)))

    return apply_fade(img, f, dur)

def draw_tc_ctx(draw, cx, y, card_w, text, font, color):
    """Center text within a card context."""
    txt_w2 = tw(draw, text, font)
    draw_t(draw, cx + (card_w - txt_w2) // 2, y, text, font, color)

# ============================================================
# FADE & RENDER DISPATCH
# ============================================================
def apply_fade(img, local_frame, duration):
    """Apply fade-in at start and fade-out at end of scene."""
    alpha = 0.0
    if local_frame < FADE:
        alpha = 1.0 - local_frame / FADE
    elif local_frame > duration - FADE:
        alpha = (local_frame - (duration - FADE)) / FADE

    if alpha <= 0.005:
        return img
    if alpha >= 0.995:
        return Image.new('RGB', (W, H), C_BLACK)

    overlay = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * alpha)))
    r = img.copy().convert('RGBA')
    r.paste(overlay, (0, 0), overlay)
    return r.convert('RGB')

def render_frame(frame_num):
    """Render a single frame. Returns PIL Image."""
    for idx, (start, end) in enumerate(SCENES):
        if start <= frame_num < end:
            local = frame_num - start
            dur = end - start
            renderers = [render_opening, render_about, render_skills,
                         render_experience, render_closing]
            return renderers[idx](local, dur)
    # Fallback (shouldn't happen)
    return Image.new('RGB', (W, H), C_BLACK)

# ============================================================
# MAIN
# ============================================================
def main():
    print("Loading fonts...")
    init_fonts()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'self_intro.avi')
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    writer = cv2.VideoWriter(output_path, fourcc, FPS, (W, H))

    if not writer.isOpened():
        print("ERROR: Could not open VideoWriter.")
        print("Try a different codec. Known working: MJPG")
        return

    print(f"Generating {TOTAL_FRAMES} frames ({TOTAL_FRAMES // FPS}s) at {W}x{H}...")
    print(f"Output: {output_path}")
    print("Progress: ", end='', flush=True)

    update_every = 30  # print progress every N frames

    try:
        for frame_num in range(TOTAL_FRAMES):
            pil_img = render_frame(frame_num)
            # PIL RGB → numpy BGR
            np_frame = np.array(pil_img)
            np_frame_bgr = cv2.cvtColor(np_frame, cv2.COLOR_RGB2BGR)
            writer.write(np_frame_bgr)

            if frame_num % update_every == 0:
                pct = (frame_num + 1) / TOTAL_FRAMES * 100
                done = int(pct / 5)
                bar = '#' * done + '.' * (20 - done)
                print(f"\rProgress: [{bar}] {pct:.0f}%", end='', flush=True)

        print(f"\rProgress: [####################] 100%")
        print("Done!")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        writer.release()

    # Show file info
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nOutput: {output_path}")
    print(f"Size:   {size_mb:.1f} MB")
    print(f"Format: AVI (MJPG), {W}x{H}, {FPS}fps, {TOTAL_FRAMES // FPS}s")
    print("\nOpen with any media player (VLC, Windows Media Player, etc.)")

if __name__ == '__main__':
    main()
