"""一键下载 Qwen3 本地模型（从 HuggingFace）。

用法: python download_models.py
"""

import os
import sys

MODELS = [
    ("Qwen/Qwen3-Embedding-0.6B", "model_cache/Qwen3-Embedding-0.6B"),
    ("Qwen/Qwen3-Reranker-0.6B", "model_cache/Qwen3-Reranker-0.6B"),
]

if __name__ == "__main__":
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("请先安装 huggingface_hub: pip install huggingface-hub")
        sys.exit(1)

    os.makedirs("model_cache", exist_ok=True)

    for repo_id, local_dir in MODELS:
        if os.path.isdir(local_dir) and os.listdir(local_dir):
            print(f"已存在，跳过: {local_dir}")
            continue
        print(f"正在下载 {repo_id} -> {local_dir} ...")
        snapshot_download(repo_id, local_dir=local_dir)
        print(f"完成: {local_dir}")

    print("\n模型下载完成！")
