"""⚠️ 数据库重置脚本 — 会永久删除所有数据！

用法: python reset_db.py
      然后输入 YES 确认。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("数据库文件不存在，无需重置。")
        sys.exit(0)

    confirm = input("⚠️ 这将永久删除所有数据！输入 YES 确认: ")
    if confirm != "YES":
        print("已取消。")
        sys.exit(0)

    # Create backup before destroying
    import shutil
    from datetime import datetime
    backup_dir = os.path.join(os.path.dirname(__file__), "db_backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"app_{ts}_pre_reset.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"备份已保存至: {backup_path}")

    # Delete DB and related files
    os.remove(DB_PATH)
    for suffix in ("-wal", "-shm"):
        wal_path = DB_PATH + suffix
        if os.path.exists(wal_path):
            os.remove(wal_path)

    # Remove skill graph cache
    graph_path = os.path.join(os.path.dirname(__file__), "skill_graph.json")
    if os.path.exists(graph_path):
        os.remove(graph_path)

    print("数据库已重置。运行 python seed.py 重新灌入演示数据。")
