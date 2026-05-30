"""演示数据种子脚本 — 一键重建数据库并灌入预置用户和需求。"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import Base, engine, async_session
from app.core.security import hash_password
from sqlalchemy import select
from app.models.user import User
from app.models.need import Need
from app.models.match import Match
from app.models.message import Message
from app.knowledge.skill_graph import get_skill_graph

SCHOOL = "绵阳城市学院"

SEED_USERS = [
    {"username": "alice", "password": "123456", "bio": "人工智能大三，会Python爬虫和Vue.js，想找队友做大创项目", "school": SCHOOL, "rating": 5.0,
     "campus": "安州校区", "college": "人工智能学院", "major": "计算机科学与技术", "town": "花荄镇"},
    {"username": "bob", "password": "123456", "bio": "智能制造研二，精通Python数据分析、ECharts可视化、机器学习，有多个实验项目经验", "school": SCHOOL, "rating": 4.8,
     "campus": "安州校区", "college": "智能制造与工程学院", "major": "机械设计制造及其自动化", "town": "黄土镇"},
    {"username": "carol", "password": "123456", "bio": "人工智能大四，React和Node.js全栈，做过多个上线项目，目前在安州校区创业园", "school": SCHOOL, "rating": 4.5,
     "campus": "安州校区", "college": "人工智能学院", "major": "软件工程", "town": "界牌镇"},
    {"username": "dave", "password": "123456", "bio": "智能制造大三，会单片机开发和3D打印，想找人一起做智能硬件创业项目", "school": SCHOOL, "rating": 4.2,
     "campus": "安州校区", "college": "智能制造与工程学院", "major": "智能制造工程", "town": "花荄镇"},
    {"username": "eve", "password": "123456", "bio": "创意设计大三，擅长UI/UX设计、Figma、品牌视觉，想找开发队友做大创", "school": SCHOOL, "rating": 4.9,
     "campus": "安州校区", "college": "创意设计学院", "major": "产品设计", "town": "塔水镇"},
    {"username": "frank", "password": "123456", "bio": "人工智能大二，参加过蓝桥杯省赛，擅长算法和数学建模，想找队友打比赛", "school": SCHOOL, "rating": 4.6,
     "campus": "安州校区", "college": "人工智能学院", "major": "计算机科学与技术", "town": "秀水镇"},
    {"username": "grace", "password": "123456", "bio": "健康与教育大三，学前教育专业，会弹钢琴和手工制作，想找设计同学做教具", "school": SCHOOL, "rating": 4.3,
     "campus": "游仙校区", "college": "健康与教育学院", "major": "学前教育", "town": "桑枣镇"},
    {"username": "henry", "password": "123456", "bio": "商学院大四，擅长商业计划书撰写、市场分析、BP路演，有创业比赛获奖经历", "school": SCHOOL, "rating": 4.7,
     "campus": "游仙校区", "college": "商学院", "major": "工商管理", "town": "花荄镇"},
    {"username": "iris", "password": "123456", "bio": "人工智能研二，精通PyTorch、目标检测、图像分割，发表过两篇论文", "school": SCHOOL, "rating": 4.9,
     "campus": "安州校区", "college": "人工智能学院", "major": "计算机科学与技术", "town": "河清镇"},
    {"username": "jack", "password": "123456", "bio": "智能制造大三，全栈开发，Vue+Spring Boot，做过校园二手交易小程序", "school": SCHOOL, "rating": 4.4,
     "campus": "安州校区", "college": "智能制造与工程学院", "major": "电气工程及其自动化", "town": "雎水镇"},
]

SEED_NEEDS = [
    {"type": "组队", "title": "大创项目数据可视化看板", "description": "需要会Python爬虫和ECharts的同学一起做大创，前端Vue我已经写了，缺数据处理和可视化，安州校区的优先"},
    {"type": "求助", "title": "智能硬件3D建模求助", "description": "在花荄镇的创业项目需要做产品外壳3D建模，会SolidWorks或Fusion360的同学请联系我"},
    {"type": "技能交换", "title": "前端换算法辅导", "description": "我擅长Vue/React前端开发，想换数据结构与算法辅导，准备秋招刷题，最好是安州校区的"},
    {"type": "组队", "title": "蓝桥杯/数学建模组队", "description": "2026数学建模竞赛组队，需要会建模和写作的同学各一人，本人负责编程，安州校区"},
    {"type": "求助", "title": "创业BP商业计划书指导", "description": "大创项目要交BP了，需要商学院的同学校准一下商业模型和财务预测，游仙校区也可以"},
]


async def seed():
    # Only create tables (never drop) — safe to run on existing DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check if already seeded (users exist)
    from app.models.user import User as U
    async with async_session() as check_db:
        r = await check_db.execute(select(U).limit(1))
        if r.scalar_one_or_none():
            print("Database already has users, skipping seed.")
            print("Login with existing accounts.")
            return

    async with async_session() as db:
        users = []
        for u in SEED_USERS:
            user = User(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                bio=u["bio"],
                school=u["school"],
                rating_score=u["rating"],
                extra={
                    "campus": u.get("campus", ""),
                    "college": u.get("college", ""),
                    "major": u.get("major", ""),
                    "town": u.get("town", ""),
                },
            )
            db.add(user)
            users.append(user)
        await db.commit()
        for u in users:
            await db.refresh(u)

        # Create needs
        needs = []
        for i, n in enumerate(SEED_NEEDS):
            author = users[i % len(users)]
            need = Need(
                user_id=author.id,
                type=n["type"],
                title=n["title"],
                description=n["description"],
                status="开放",
            )
            db.add(need)
            needs.append(need)
        await db.commit()
        for n in needs:
            await db.refresh(n)

        # Pre-populate some matches (for demo)
        match1 = Match(
            need_id=needs[0].id,
            user_id=users[1].id,  # bob matches alice's 数据可视化 need
            score=94.0,
            ai_reason="Bob精通ECharts和Python数据分析，技能重合度94%，上学期刚完成类似项目",
        )
        match2 = Match(
            need_id=needs[0].id,
            user_id=users[8].id,  # iris also matches
            score=82.0,
            ai_reason="Iris有CVPR论文，对数据可视化有深入理解，不同校但技能高度匹配",
        )
        match3 = Match(
            need_id=needs[1].id,
            user_id=users[3].id,  # dave matches SEM need
            score=96.0,
            ai_reason="Dave精通SEM/XRD/TEM三种表征，同校、同院系，可立即协助",
        )
        match4 = Match(
            need_id=needs[3].id,
            user_id=users[5].id,  # frank matches 美赛
            score=88.0,
            ai_reason="Frank有ACM银牌背景，数学建模能力突出，同校便于组队",
        )
        db.add_all([match1, match2, match3, match4])

        # Pre-populate some messages
        msg1 = Message(need_id=needs[0].id, sender_id=users[0].id, receiver_id=users[1].id, content="你好Bob！看到你的技能很匹配，一起做大创吗？")
        msg2 = Message(need_id=needs[0].id, sender_id=users[1].id, receiver_id=users[0].id, content="Alice你好！我也正在找数据可视化的队友，我们可以聊聊")
        db.add_all([msg1, msg2])

        # Build skill graph from users
        graph = get_skill_graph()
        from app.skills.registry import SkillRegistry
        from app.skills.tag_skill import TagSkill
        from app.skills.embed_skill import EmbedSkill

        SkillRegistry.register(TagSkill())
        SkillRegistry.register(EmbedSkill())

        for user in users:
            if user.bio:
                tag_skill = SkillRegistry.get("tag_extraction")
                result = await tag_skill.execute({"text": user.bio})
                tags = result.get("tags", [])
                if tags:
                    user.skill_tags = tags
                    embed_skill = SkillRegistry.get("embedding")
                    emb = await embed_skill.execute({"text": " ".join(tags)})
                    user.profile_embedding = emb["embedding"]
                    graph.add_co_occurrence(tags)

        for need in needs:
            tag_skill = SkillRegistry.get("tag_extraction")
            result = await tag_skill.execute({"text": need.description})
            tags = result.get("tags", [])
            if tags:
                need.req_tags = tags
                embed_skill = SkillRegistry.get("embedding")
                emb = await embed_skill.execute({"text": " ".join(tags)})
                need.need_embedding = emb["embedding"]

        await db.commit()
        graph.to_file("skill_graph.json")

    print(f"Seeded {len(users)} users, {len(needs)} needs, 4 matches, 2 messages")
    print("Demo data ready!")
    print("\nLogin with any username from above (password: 123456)")


if __name__ == "__main__":
    asyncio.run(seed())
