"""
Email MCP Server — FastMCP 버전
Gmail SMTP를 통한 이메일 발송 도구 (앱 비밀번호 사용)
"""

import os
import smtplib
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("email-mcp-server")


def _smtp_connect() -> smtplib.SMTP:
    """Gmail SMTP TLS 연결을 반환합니다."""
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(
        os.getenv("GMAIL_EMAIL", ""),
        os.getenv("GMAIL_APP_PASSWORD", ""),
    )
    return server


def _check_config() -> str | None:
    """이메일 설정 유효성 검사. 문제 있으면 오류 메시지 반환."""
    if not os.getenv("GMAIL_EMAIL"):
        return "오류: .env에 GMAIL_EMAIL이 설정되지 않았습니다."
    if not os.getenv("GMAIL_APP_PASSWORD"):
        return (
            "Gmail 앱 비밀번호가 설정되지 않았습니다.\n"
            "myaccount.google.com > 보안 > 앱 비밀번호 에서 16자리 비밀번호를 발급하세요."
        )
    return None


def _build_message(
    to: str, subject: str, body: str, cc: str = ""
) -> tuple[MIMEMultipart, list[str], str]:
    """MIMEMultipart 메시지와 수신자 목록을 반환합니다."""
    from_addr = os.getenv("GMAIL_EMAIL", "")
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = str(Header(subject, "utf-8"))
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))
    recipients = [t.strip() for t in to.split(",")]
    if cc:
        recipients += [c.strip() for c in cc.split(",")]
    return msg, recipients, from_addr


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
) -> str:
    """Gmail SMTP로 이메일을 발송합니다. 보내는 사람은 .env에 등록된 계정이 자동 사용됩니다.

    Args:
        to: 받는 사람 이메일 주소 (여러 명은 쉼표로 구분)
        subject: 이메일 제목
        body: 이메일 본문 내용
        cc: 참조(CC) 이메일 주소 (선택)
    """
    err = _check_config()
    if err:
        return err

    msg, recipients, from_addr = _build_message(to, subject, body, cc)
    try:
        with _smtp_connect() as server:
            server.sendmail(from_addr, recipients, msg.as_string())
        cc_info = f"\n참조: {cc}" if cc else ""
        return f"이메일 발송 완료\n보낸 사람: {from_addr}\n받는 사람: {to}{cc_info}\n제목: {subject}"
    except smtplib.SMTPAuthenticationError:
        return (
            "인증 실패: 앱 비밀번호를 확인하세요.\n"
            "일반 Gmail 비밀번호는 사용 불가 — 16자리 앱 비밀번호가 필요합니다.\n"
            "myaccount.google.com > 보안 > 앱 비밀번호"
        )
    except Exception as e:
        return f"발송 실패: {e}"


@mcp.tool()
def send_email_with_attachment(
    to: str,
    subject: str,
    body: str,
    file_path: str,
    cc: str = "",
) -> str:
    """파일을 첨부하여 Gmail SMTP로 이메일을 발송합니다.

    Args:
        to: 받는 사람 이메일 주소
        subject: 이메일 제목
        body: 이메일 본문 내용
        file_path: 첨부할 파일 경로 (Excel, PDF, PNG 등)
        cc: 참조(CC) 이메일 주소 (선택)
    """
    err = _check_config()
    if err:
        return err
    if not Path(file_path).exists():
        return f"오류: 파일을 찾을 수 없습니다 — {file_path}"

    msg, recipients, from_addr = _build_message(to, subject, body, cc)

    filename = Path(file_path).name
    with open(file_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=("utf-8", "", filename),
    )
    msg.attach(part)

    file_kb = Path(file_path).stat().st_size / 1024
    try:
        with _smtp_connect() as server:
            server.sendmail(from_addr, recipients, msg.as_string())
        cc_info = f"\n참조: {cc}" if cc else ""
        return (
            f"이메일 발송 완료\n"
            f"보낸 사람: {from_addr}\n받는 사람: {to}{cc_info}\n"
            f"제목: {subject}\n첨부 파일: {filename} ({file_kb:.1f} KB)"
        )
    except smtplib.SMTPAuthenticationError:
        return (
            "인증 실패: 앱 비밀번호를 확인하세요.\n"
            "myaccount.google.com > 보안 > 앱 비밀번호"
        )
    except Exception as e:
        return f"발송 실패: {e}"


if __name__ == "__main__":
    mcp.run(show_banner=False)
