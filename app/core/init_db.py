import json
import os
from sqlalchemy import select
from app.core.database import engine, AsyncSessionLocal
from app.models.entities import Base, MajorCatalog
from app.core.logger import logger

async def init_database():
    """
    初始化数据库：自动创建表结构并载入标准专业目录种子数据
    """
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")

    # 检查并载入专业目录种子数据
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(MajorCatalog).limit(1))
        existing = res.scalars().first()
        if not existing:
            catalog_file = "data/catalogs/preventive_medicine_2024.json"
            if os.path.exists(catalog_file):
                logger.info(f"Seeding default major catalog from {catalog_file}...")
                with open(catalog_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        catalog = MajorCatalog(
                            version_year=item["version_year"],
                            degree_level=item["degree_level"],
                            category_code=item["category_code"],
                            major_code=item["major_code"],
                            major_name=item["major_name"],
                            match_weight=item.get("match_weight", 5),
                            remarks=item.get("remarks", "")
                        )
                        session.add(catalog)
                await session.commit()
                logger.info("Default major catalog seeded successfully.")
