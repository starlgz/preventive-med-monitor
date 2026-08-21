import smtplib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from typing import Dict, Any, Optional
from loguru import logger
from app.core.config import settings
from app.notifications.base import BaseChannel

_executor = ThreadPoolExecutor(max_workers=3)

class EmailChannel(BaseChannel):
    """SMTP 邮件通知推送实现 (基于标准库 smtplib 异步线程池包装)"""

    def __init__(self, smtp_host: Optional[str] = None, smtp_port: Optional[int] = None,
                 username: Optional[str] = None, password: Optional[str] = None,
                 receiver_email: Optional[str] = None):
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.receiver_email = receiver_email or settings.EMAIL_RECEIVER

    @property
    def channel_name(self) -> str:
        return "email"

    def format_job_card(self, job_data: Dict[str, Any]) -> str:
        """
        生成带有 HTML 样式的邮件正文排版
        """
        unit = job_data.get("unit_name", "未知单位")
        job = job_data.get("job_name", "公卫相关岗位")
        headcount = job_data.get("headcount", 1)
        edu = job_data.get("education", "本科及以上")
        major = job_data.get("major_raw", "预防医学")
        star = job_data.get("match_level", 5)
        
        bz = job_data.get("is_bianzhi", 1)
        bz_type = job_data.get("bianzhi_type", "事业编制")
        bz_color = "#28a745" if bz == 1 else ("#ffc107" if bz == 2 else "#dc3545")
        bz_tag = f"<span style='color: {bz_color}; font-weight: bold;'>{'🟢 事业编制' if bz == 1 else ('🟡 备案/存疑' if bz == 2 else '🔴 编外合同')}</span>"
        
        priority = job_data.get("priority_level", "A")
        deadline = job_data.get("apply_end_date", "详见招考公告")
        url = job_data.get("source_url", "#")
        certs = job_data.get("cert_requirements", "无明确限制")
        age = job_data.get("age_limit_num", "按公告执行")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #0056b3; color: #ffffff; padding: 15px 20px;">
                <h3 style="margin: 0;">🎯 【{priority}级预警】{unit} - 招聘速报</h3>
            </div>
            <div style="padding: 20px; background-color: #fcfcfc;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px 0; color: #666; width: 90px;">招考单位：</td><td style="font-weight: bold;">{unit}</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">招聘岗位：</td><td>{job}（招 <b>{headcount}</b> 人）</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">专业匹配：</td><td style="color: #ff9800; font-weight: bold;">{star} 星级对口</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">编制性质：</td><td>{bz_tag}（{bz_type}）</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">学历/专业：</td><td>{edu} | {major}</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">资格证书：</td><td>{certs}</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">年龄限制：</td><td>{age}周岁以下</td></tr>
                    <tr><td style="padding: 8px 0; color: #666;">报名截止：</td><td style="color: #d9534f; font-weight: bold;">{deadline}</td></tr>
                </table>
                <div style="margin-top: 20px; text-align: center;">
                    <a href="{url}" style="display: inline-block; padding: 10px 24px; background-color: #0056b3; color: #ffffff; text-decoration: none; border-radius: 4px; font-weight: bold;">查看官方招考公告</a>
                </div>
            </div>
            <div style="background-color: #f1f1f1; padding: 10px 20px; font-size: 12px; color: #888; text-align: center;">
                全国预防医学事业单位招聘实时监测系统 · 自动推送
            </div>
        </div>
        """
        return html

    def _sync_send(self, title: str, content: str) -> bool:
        message = EmailMessage()
        message["From"] = self.username
        message["To"] = self.receiver_email
        message["Subject"] = title
        message.set_content("请使用支持 HTML 的邮件客户端查看此邮件。")
        message.add_alternative(content, subtype="html")

        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                if self.smtp_port == 587:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.send_message(message)
            server.quit()
            logger.info(f"Email notification sent to {self.receiver_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    async def send(self, title: str, content: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        if not self.smtp_host or not self.username or not self.receiver_email:
            logger.warning("SMTP configuration incomplete, mock sending email.")
            return True

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self._sync_send, title, content)
