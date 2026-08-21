from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Text, Float, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class MajorCatalog(Base):
    """
    教育部标准专业目录表 (按年份、本硕博、专业代码独立管理)
    """
    __tablename__ = "major_catalogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_year: Mapped[int] = mapped_column(Integer, index=True)          # 目录年份 (如 2024)
    degree_level: Mapped[str] = mapped_column(String(32), index=True)        # undergraduate(本科) / graduate(研究生) / doctorate(博士)
    category_code: Mapped[str] = mapped_column(String(32))                   # 门类/一级学科代码 (如 1004)
    major_code: Mapped[str] = mapped_column(String(32), index=True)          # 专业代码 (如 100401K)
    major_name: Mapped[str] = mapped_column(String(128), index=True)         # 专业名称 (如 预防医学)
    match_weight: Mapped[int] = mapped_column(Integer, default=5)            # 基础匹配权重 (1-5)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)               # 是否启用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Source(Base):
    """
    招聘信息源插件表
    """
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), unique=True, index=True) # 插件唯一标识 (如 chinagwy_wszp)
    name: Mapped[str] = mapped_column(String(128))                             # 来源名称
    category: Mapped[str] = mapped_column(String(32))                          # official / aggregate / search
    province: Mapped[str] = mapped_column(String(32), default="全国")          # 归属省份
    base_url: Mapped[str] = mapped_column(String(255))
    driver_type: Mapped[str] = mapped_column(String(32), default="http")       # http / playwright
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    health_score: Mapped[float] = mapped_column(Float, default=1.0)           # 健康分 (0.0~1.0)
    last_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    announcements: Mapped[List["Announcement"]] = relationship("Announcement", back_populates="source_rel")

class Announcement(Base):
    """
    原始招聘公告表
    """
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.source_id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # 原始正文
    province: Mapped[Optional[str]] = mapped_column(String(32), nullable=True) # 归属省份
    city: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)     # 归属城市
    simhash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    crawl_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_processed: Mapped[int] = mapped_column(Integer, default=0)              # 0:待提取, 1:已提取, -1:解析失败

    source_rel: Mapped["Source"] = relationship("Source", back_populates="announcements")
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="announcement")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="announcement")

class Attachment(Base):
    """
    公告附件表 (岗位表 Excel / PDF / Word)
    """
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey("announcements.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16))                         # xlsx / xls / pdf / docx / doc / zip
    local_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending")   # pending / success / failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="attachments")

class Job(Base):
    """
    结构化招聘岗位表 (核心)
    编制判断以岗位为最小粒度
    """
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey("announcements.id"), index=True)
    job_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True) # 唯一指纹

    # 招考单位与归属
    unit_name: Mapped[str] = mapped_column(String(128), index=True)            # 招聘单位
    unit_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)# cdc(疾控) / hospital(医院) / gov(卫健委) / other
    province: Mapped[str] = mapped_column(String(32), index=True)
    city: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 岗位基础信息
    job_name: Mapped[str] = mapped_column(String(128), index=True)             # 岗位名称
    job_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # 岗位代码
    headcount: Mapped[int] = mapped_column(Integer, default=1)                 # 招聘人数

    # 学历与专业要求
    education: Mapped[str] = mapped_column(String(32), default="本科及以上")
    degree: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    major_raw: Mapped[str] = mapped_column(Text)                               # 原始专业要求文本
    matched_major_codes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # 命中的专业代码JSON

    # 核心评级与编制 (以岗位为最小单位)
    match_level: Mapped[int] = mapped_column(Integer, index=True, default=1)  # 1-5 星
    is_bianzhi: Mapped[int] = mapped_column(Integer, index=True, default=0)   # 1:在编, 0:非编, 2:存疑
    bianzhi_type: Mapped[str] = mapped_column(String(32), default="uncertain")# official(在编) / non_official(非编) / uncertain(存疑)
    bianzhi_confidence: Mapped[float] = mapped_column(Float, default=0.0)      # 置信度 (0.0~1.0)
    bianzhi_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 判定证据原句 JSON

    # 门槛特征画像
    is_fresh_grad: Mapped[int] = mapped_column(Integer, default=0)             # 1:限应届, 0:不限, 2:限往届
    cert_requirements: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # 医师资格等
    is_training_required: Mapped[int] = mapped_column(Integer, default=0)      # 是否要求规培证
    residency_limit: Mapped[Optional[str]] = mapped_column(String(128), nullable=True) # 户籍生源限制
    age_limit_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 年龄上限 (如 35)
    talent_tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # 人才政策标签 (免笔试/安家费等)
    talent_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 人才政策证据链与详情说明

    # 报名时间与考务
    apply_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    apply_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    exam_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # AI 研判
    ai_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True) # 推荐报名 / 需人工确认 / 不推荐
    ai_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 通知优先级预留 (S / A / B / C / D)
    priority_level: Mapped[str] = mapped_column(String(8), index=True, default="C")

    # 用户交互状态
    user_status: Mapped[str] = mapped_column(String(32), default="new")        # new / starred / applied / ignored
    last_change_type: Mapped[str] = mapped_column(String(32), default="new")  # new / updated_deadline
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="jobs")

class CrawlLog(Base):
    """
    爬虫运行与监控日志表
    """
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.source_id"), index=True)
    status: Mapped[str] = mapped_column(String(32))                            # SUCCESS / FAILED / WARNING
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_extracted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Notification(Base):
    """
    通知历史表 (防止重复打扰)
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32))                           # telegram / webhook / wechat / email
    priority_level: Mapped[str] = mapped_column(String(8))                     # S / A / B / C / D
    status: Mapped[str] = mapped_column(String(32), default="SENT")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_unique_job_channel", "job_id", "channel", unique=True),
    )

class UserFilter(Base):
    """
    用户偏好过滤表
    """
    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    filter_name: Mapped[str] = mapped_column(String(64))
    target_provinces: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_degrees: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    only_bianzhi: Mapped[int] = mapped_column(Integer, default=1)
    min_match_level: Mapped[int] = mapped_column(Integer, default=4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Favorite(Base):
    """
    岗位收藏表
    """
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Application(Base):
    """
    已报考岗位跟踪表
    """
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    progress_status: Mapped[str] = mapped_column(String(32), default="applied") # applied / written_passed / interview_passed / offered
    exam_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
