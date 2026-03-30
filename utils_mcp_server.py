"""
Utility MCP Server — FastMCP 버전
웹 검색 · 날짜/시간 · 파일 관리 · 차트 생성 도구
"""

import json
import os
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("utils-mcp-server")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo를 사용해 인터넷에서 정보를 검색합니다. 최신 뉴스, 일반 지식, 제품 정보 등을 찾을 때 사용합니다.

    Args:
        query: 검색할 키워드 또는 문장
        max_results: 반환할 최대 결과 수 (기본값: 5)
    """
    from duckduckgo_search import DDGS

    results = list(DDGS().text(query, max_results=max_results))
    if not results:
        return f"'{query}' 에 대한 검색 결과가 없습니다."

    lines = [f"검색어: {query}  |  결과 {len(results)}건\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')}")
        lines.append(f"    {r.get('href', '')}")
        body = r.get("body", "")
        if body:
            lines.append(f"    {body[:250]}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_current_datetime() -> str:
    """현재 날짜와 시각을 반환합니다."""
    now = datetime.now()
    weekdays = {
        "Monday": "월요일", "Tuesday": "화요일", "Wednesday": "수요일",
        "Thursday": "목요일", "Friday": "금요일", "Saturday": "토요일", "Sunday": "일요일",
    }
    day_kor = weekdays.get(now.strftime("%A"), now.strftime("%A"))
    return f"현재 날짜/시각: {now.strftime(f'%Y년 %m월 %d일 ({day_kor}) %H:%M:%S')}"


@mcp.tool()
def list_files(directory_path: str, extension: str = "") -> str:
    """지정한 디렉토리 안의 파일과 폴더 목록을 반환합니다.

    Args:
        directory_path: 조회할 디렉토리 경로
        extension: 특정 확장자만 필터링 (예: .xlsx, .csv, .txt). 생략 시 전체 표시
    """
    if not os.path.exists(directory_path):
        return f"디렉토리를 찾을 수 없습니다: {directory_path}"

    entries = []
    for entry in sorted(Path(directory_path).iterdir()):
        if extension and not entry.name.endswith(extension):
            continue
        if entry.is_file():
            size = entry.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
            entries.append(f"  [파일] {entry.name:<40} {size_str}")
        else:
            entries.append(f"  [폴더] {entry.name}/")

    if not entries:
        return f"'{directory_path}' 에 조건에 맞는 항목이 없습니다."
    return f"디렉토리: {directory_path}  ({len(entries)}개 항목)\n" + "\n".join(entries)


@mcp.tool()
def read_text_file(file_path: str, max_lines: int = 100) -> str:
    """텍스트(.txt), CSV(.csv), JSON(.json) 파일을 읽어 내용을 반환합니다.

    Args:
        file_path: 읽을 파일 경로
        max_lines: 최대 읽을 줄 수 (기본값: 100)
    """
    if not os.path.exists(file_path):
        return f"파일을 찾을 수 없습니다: {file_path}"

    ext = Path(file_path).suffix.lower()

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return f"JSON 파일: {file_path}\n\n{json.dumps(data, ensure_ascii=False, indent=2)}"

    if ext == ".csv":
        import pandas as pd
        df = pd.read_csv(file_path, nrows=max_lines)
        return f"CSV 파일: {file_path}  ({df.shape[0]}행 × {df.shape[1]}열)\n\n{df.to_string()}"

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    total = len(lines)
    content = "".join(lines[:max_lines])
    suffix = f"\n\n... ({total}줄 중 {max_lines}줄 표시)" if total > max_lines else ""
    return f"파일: {file_path}\n\n{content}{suffix}"


@mcp.tool()
def create_chart(
    chart_type: str,
    title: str,
    labels: list[str],
    values: list[float],
    save_path: str,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """막대(bar), 선(line), 원형(pie) 차트를 생성하고 PNG 이미지로 저장합니다.

    Args:
        chart_type: 차트 종류 — bar(막대), line(선), pie(원형)
        title: 차트 제목
        labels: X축 레이블 또는 파이 차트 항목명 목록
        values: 각 항목의 수치 데이터
        save_path: 저장할 PNG 파일 경로 (예: chart.png)
        x_label: X축 이름 (선택)
        y_label: Y축 이름 (선택)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    PALETTE = ["#2D3748", "#553C9A", "#2B6CB0", "#276749", "#C05621",
               "#702459", "#1A365D", "#44337A", "#1C4532", "#7B341E"]

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    if chart_type == "bar":
        bars = ax.bar(labels, values, color=PALETTE[:len(labels)],
                      edgecolor="white", linewidth=0.8, width=0.6)
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.012,
                f"{val:,.0f}", ha="center", va="bottom", fontsize=9, color="#2D3748",
            )
        ax.grid(axis="y", alpha=0.25, linestyle="--", color="#A0AEC0")
        ax.set_axisbelow(True)
        if x_label:
            ax.set_xlabel(x_label, fontsize=10)
        if y_label:
            ax.set_ylabel(y_label, fontsize=10)

    elif chart_type == "line":
        ax.plot(range(len(labels)), values, color=PALETTE[0],
                marker="o", linewidth=2.5, markersize=7,
                markerfacecolor="white", markeredgewidth=2)
        ax.fill_between(range(len(labels)), values, alpha=0.08, color=PALETTE[0])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.grid(alpha=0.25, linestyle="--", color="#A0AEC0")
        ax.set_axisbelow(True)
        if x_label:
            ax.set_xlabel(x_label, fontsize=10)
        if y_label:
            ax.set_ylabel(y_label, fontsize=10)

    elif chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%",
            colors=PALETTE[:len(labels)], startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
            pctdistance=0.82,
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_color("white")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#E2E8F0")
    ax.spines["bottom"].set_color("#E2E8F0")
    ax.tick_params(colors="#4A5568")
    ax.set_title(title, fontsize=15, fontweight="bold", color="#1A202C", pad=16)
    plt.tight_layout()

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return f"차트 저장 완료: {save_path}"


if __name__ == "__main__":
    mcp.run(show_banner=False)
