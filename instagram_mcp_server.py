"""
Instagram MCP Server — FastMCP 버전
이미지 생성(텍스트 합성) + Instagram 자동 포스팅
"""

import os
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("instagram-mcp-server")

# Windows 한글 폰트 경로 (없으면 기본 폰트 사용)
_FONT_BOLD   = "C:/Windows/Fonts/malgunbd.ttf"   # 맑은 고딕 Bold
_FONT_NORMAL = "C:/Windows/Fonts/malgun.ttf"      # 맑은 고딕


def _get_font(size: int, bold: bool = False):
    from PIL import ImageFont
    path = _FONT_BOLD if bold else _FONT_NORMAL
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    """주어진 폭에 맞게 텍스트를 줄바꿈합니다."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines if lines else [text]


# ─────────────────────────────────────────
# 이미지 도구
# ─────────────────────────────────────────

@mcp.tool()
def add_text_to_image(
    image_path: str,
    text: str,
    output_path: str = "",
    font_size: int = 48,
    text_color: str = "white",
    position: str = "center",
    shadow: bool = True,
    overlay_opacity: int = 40,
) -> str:
    """기존 사진 위에 텍스트(글귀)를 합성합니다.

    Args:
        image_path: 원본 사진 파일 경로 (JPG, PNG)
        text: 사진에 넣을 글귀 (줄바꿈은 \\n 사용)
        output_path: 저장할 파일 경로 (비워두면 원본명_text.jpg로 저장)
        font_size: 글자 크기 (기본: 48)
        text_color: 글자 색상 — white, black, yellow, #RRGGBB (기본: white)
        position: 텍스트 위치 — center, top, bottom (기본: center)
        shadow: 텍스트 그림자 효과 (기본: True)
        overlay_opacity: 텍스트 가독성을 위한 어두운 오버레이 투명도 0~100 (기본: 40)
    """
    from PIL import Image, ImageDraw, ImageFont

    if not Path(image_path).exists():
        return f"오류: 이미지 파일을 찾을 수 없습니다 — {image_path}"

    if not output_path:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_text{p.suffix}")

    img = Image.open(image_path).convert("RGBA")
    W, H = img.size

    # 어두운 반투명 오버레이 (텍스트 가독성)
    if overlay_opacity > 0:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * overlay_opacity / 100)))
        img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    font = _get_font(font_size, bold=True)
    padding = int(W * 0.08)

    # 텍스트 색 파싱
    if text_color.startswith("#"):
        r = int(text_color[1:3], 16)
        g = int(text_color[3:5], 16)
        b = int(text_color[5:7], 16)
        fill = (r, g, b, 255)
    else:
        color_map = {
            "white": (255, 255, 255, 255),
            "black": (0, 0, 0, 255),
            "yellow": (255, 230, 80, 255),
            "red": (255, 80, 80, 255),
        }
        fill = color_map.get(text_color.lower(), (255, 255, 255, 255))

    # 줄바꿈 처리
    raw_lines = text.replace("\\n", "\n").split("\n")
    lines = []
    for raw in raw_lines:
        lines.extend(_wrap_text(raw, font, W - padding * 2, draw))

    line_h = font_size + int(font_size * 0.3)
    total_h = line_h * len(lines)

    if position == "top":
        start_y = int(H * 0.12)
    elif position == "bottom":
        start_y = H - total_h - int(H * 0.12)
    else:
        start_y = (H - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        y = start_y + i * line_h

        if shadow:
            offset = max(2, font_size // 20)
            draw.text((x + offset, y + offset), line, font=font, fill=(0, 0, 0, 160))

        draw.text((x, y), line, font=font, fill=fill)

    result = img.convert("RGB")
    result.save(output_path, quality=95)
    return f"이미지 텍스트 합성 완료\n저장 경로: {output_path}\n크기: {W}×{H}px\n글줄 수: {len(lines)}줄"


@mcp.tool()
def create_text_image(
    text: str,
    output_path: str = "instagram_post.jpg",
    width: int = 1080,
    height: int = 1080,
    bg_color: str = "#1A1A2E",
    text_color: str = "white",
    font_size: int = 60,
    sub_text: str = "",
    sub_font_size: int = 36,
) -> str:
    """글귀만으로 인스타그램 정사각형 이미지를 생성합니다 (사진 없이).

    Args:
        text: 메인 글귀 (줄바꿈은 \\n 사용)
        output_path: 저장할 파일 경로 (기본: instagram_post.jpg)
        width: 이미지 너비 px (기본: 1080)
        height: 이미지 높이 px (기본: 1080)
        bg_color: 배경색 — #RRGGBB 또는 black, white, navy, purple (기본: #1A1A2E)
        text_color: 글자 색상 (기본: white)
        font_size: 메인 글자 크기 (기본: 60)
        sub_text: 하단 부제 텍스트 (선택)
        sub_font_size: 부제 글자 크기 (기본: 36)
    """
    from PIL import Image, ImageDraw

    color_map = {
        "black": "#000000", "white": "#FFFFFF",
        "navy": "#1A1A2E", "purple": "#2D1B69",
        "gray": "#2D3748", "dark": "#111111",
    }
    bg_hex = color_map.get(bg_color.lower(), bg_color)

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    bg_rgb = hex_to_rgb(bg_hex)
    img  = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 장식선
    accent = (100, 80, 200) if bg_hex in ("#1A1A2E", "#2D1B69") else (180, 180, 180)
    draw.rectangle([width//2 - 40, height//2 - int(height*0.35),
                    width//2 + 40, height//2 - int(height*0.35) + 3], fill=accent)

    font = _get_font(font_size, bold=True)
    padding = int(width * 0.1)

    if text_color.startswith("#"):
        r, g, b = hex_to_rgb(text_color)
        fill = (r, g, b)
    else:
        fill_map = {"white": (255,255,255), "black": (0,0,0),
                    "yellow": (255,230,80), "gold": (212,175,55)}
        fill = fill_map.get(text_color.lower(), (255,255,255))

    raw_lines = text.replace("\\n", "\n").split("\n")
    lines = []
    for raw in raw_lines:
        lines.extend(_wrap_text(raw, font, width - padding * 2, draw))

    line_h = font_size + int(font_size * 0.4)
    total_h = line_h * len(lines)
    start_y = (height - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, start_y + i * line_h), line, font=font, fill=fill)

    if sub_text:
        sfont = _get_font(sub_font_size, bold=False)
        sub_fill = tuple(max(0, c - 80) for c in fill) if fill != (255,255,255) else (180,180,180)
        sbbox = draw.textbbox((0, 0), sub_text, font=sfont)
        sx = (width - (sbbox[2] - sbbox[0])) // 2
        sy = start_y + total_h + int(font_size * 0.8)
        draw.text((sx, sy), sub_text, font=sfont, fill=sub_fill)

    img.save(output_path, quality=95)
    return f"이미지 생성 완료\n저장 경로: {output_path}\n크기: {width}×{height}px"


# ─────────────────────────────────────────
# Instagram 포스팅 도구
# ─────────────────────────────────────────

def _check_instagram_config() -> str | None:
    if not os.getenv("INSTAGRAM_USERNAME"):
        return "오류: .env에 INSTAGRAM_USERNAME이 설정되지 않았습니다."
    if not os.getenv("INSTAGRAM_PASSWORD"):
        return "오류: .env에 INSTAGRAM_PASSWORD가 설정되지 않았습니다."
    return None


def _get_instagram_client():
    """instagrapi Client 로그인 후 반환 (세션 파일 재사용)"""
    from instagrapi import Client

    username = os.getenv("INSTAGRAM_USERNAME", "")
    password = os.getenv("INSTAGRAM_PASSWORD", "")
    session_file = Path(__file__).parent / f".insta_session_{username}.json"

    cl = Client()
    cl.delay_range = [1, 3]

    if session_file.exists():
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            cl.dump_settings(session_file)
            return cl
        except Exception:
            session_file.unlink(missing_ok=True)

    cl.login(username, password)
    cl.dump_settings(session_file)
    return cl


@mcp.tool()
def instagram_post(
    image_path: str,
    caption: str,
    hashtags: str = "",
) -> str:
    """Instagram에 사진을 포스팅합니다.

    Args:
        image_path: 업로드할 이미지 파일 경로 (JPG, PNG)
        caption: 게시물 본문 캡션
        hashtags: 해시태그 목록 (예: #일상 #감성 #daily). 비워두면 자동 추가 안 함
    """
    err = _check_instagram_config()
    if err:
        return err
    if not Path(image_path).exists():
        return f"오류: 이미지 파일을 찾을 수 없습니다 — {image_path}"

    full_caption = caption
    if hashtags:
        full_caption = f"{caption}\n\n{hashtags}"

    try:
        cl = _get_instagram_client()
        media = cl.photo_upload(path=image_path, caption=full_caption)
        return (
            f"Instagram 포스팅 완료!\n"
            f"게시물 ID: {media.pk}\n"
            f"이미지: {image_path}\n"
            f"캡션: {caption[:50]}{'...' if len(caption) > 50 else ''}\n"
            f"해시태그: {hashtags if hashtags else '없음'}"
        )
    except Exception as e:
        err_msg = str(e)
        if "challenge_required" in err_msg.lower():
            return (
                "Instagram 보안 확인 필요\n"
                "인스타그램 앱에서 로그인 시도 알림을 확인하고 승인해 주세요.\n"
                "이후 다시 시도하면 됩니다."
            )
        if "bad_password" in err_msg.lower() or "invalid_user" in err_msg.lower():
            return "로그인 실패: 아이디 또는 비밀번호를 확인하세요."
        return f"포스팅 실패: {err_msg}"


@mcp.tool()
def instagram_check_login() -> str:
    """Instagram 로그인 상태와 계정 정보를 확인합니다."""
    err = _check_instagram_config()
    if err:
        return err
    try:
        cl = _get_instagram_client()
        user = cl.account_info()
        return (
            f"Instagram 로그인 성공\n"
            f"사용자명: @{user.username}\n"
            f"이름: {user.full_name or '(미설정)'}\n"
            f"이메일: {user.email or '(미설정)'}\n"
            f"비공개 계정: {'예' if user.is_private else '아니요'}"
        )
    except Exception as e:
        return f"로그인 실패: {e}"


@mcp.tool()
def instagram_generate_hashtags(topic: str, count: int = 20) -> str:
    """주제에 맞는 인기 해시태그 조합을 추천합니다 (LLM 없이 키워드 기반).

    Args:
        topic: 게시물 주제 (예: 일상, 카페, 여행, 음식, 감성)
        count: 추천 해시태그 수 (기본: 20)
    """
    tag_db = {
        "일상": ["#일상", "#daily", "#오늘", "#vlog", "#일상스타그램",
                 "#데일리", "#소소한일상", "#일상공유", "#맞팔", "#좋아요"],
        "카페": ["#카페", "#cafe", "#커피", "#coffee", "#카페스타그램",
                 "#카페투어", "#카페인", "#핸드드립", "#라떼아트", "#디저트"],
        "여행": ["#여행", "#travel", "#여행스타그램", "#旅行", "#trip",
                 "#여행사진", "#국내여행", "#해외여행", "#풍경", "#감성여행"],
        "음식": ["#맛스타그램", "#먹스타그램", "#food", "#맛집", "#foodporn",
                 "#맛집탐방", "#홈쿡", "#요리", "#delicious", "#yummy"],
        "감성": ["#감성", "#감성사진", "#감성스타그램", "#mood", "#aesthetic",
                 "#감성충전", "#필름사진", "#사진스타그램", "#포토그래피", "#인생사진"],
        "자연": ["#자연", "#nature", "#풍경", "#landscape", "#하늘",
                 "#숲", "#바다", "#산", "#힐링", "#자연스타그램"],
    }
    result = []
    for key, tags in tag_db.items():
        if key in topic or topic in key:
            result.extend(tags)
    if not result:
        result = ["#일상", "#daily", "#감성", "#사진", "#photo",
                  "#스타그램", "#인스타", "#좋아요", "#맞팔", "#follow"]

    result = list(dict.fromkeys(result))[:count]
    return f"추천 해시태그 ({len(result)}개):\n" + " ".join(result)


if __name__ == "__main__":
    mcp.run()
