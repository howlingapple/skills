#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightRAG CLI 工具 (异步版本)

使用示例:
    # 加载文档
    python lightrag_cli.py load --data-path ./reference

    # 查询
    python lightrag_cli.py query "什么是数据安全？"

    # 指定查询模式
    python lightrag_cli.py query "什么是数据安全？" --mode hybrid
"""

import asyncio
import argparse
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lightrag_skill import LightRAGSkill, create_skill, load_and_index, query_index, read_documents


def _get_working_dir(config_path: str | None) -> Path:
    """从配置读取工作目录"""
    import yaml
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).parent.parent / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    work_dir = cfg.get("graphrag", {}).get("lightrag", {}).get("working_dir", "./lightrag_db")
    return Path(work_dir).resolve() if not Path(work_dir).is_absolute() else Path(work_dir)


async def cmd_load(args):
    """加载文档到索引（增量式，已有文档自动跳过）"""
    skill = await load_and_index(args.data_path, args.config)
    try:
        print(f"\n✅ 文档加载完成，索引存储在: {skill._working_dir}")
    finally:
        await skill.finalize()


async def cmd_backup(args):
    """备份当前索引（时间戳命名，保留最近 N 个备份）"""
    import datetime
    work_dir = _get_working_dir(args.config)
    if not work_dir.exists() or not list(work_dir.iterdir()):
        print("没有索引需要备份")
        return

    # 时间戳命名，先创建新备份
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = work_dir.with_name(f"{work_dir.name}.{ts}")
    work_dir.rename(bak_path)
    print(f"索引已备份到: {bak_path.name}")

    # 再清理旧备份，保留最近 N 个
    keep = getattr(args, 'keep', 3)
    backups = sorted(
        [p for p in work_dir.parent.iterdir()
         if p.name.startswith(work_dir.name + ".") and p.name != work_dir.name],
        reverse=True,
    )
    for old in backups[keep:]:
        shutil.rmtree(old)
        print(f"已清理旧备份: {old.name}")


async def cmd_insert(args):
    """增量添加文档（不备份，直接 ainsert 到现有索引）"""
    print(f"[Insert] 读取文档: {args.data_path}")
    documents = await read_documents(args.data_path)
    if not documents:
        print("没有读取到任何文档内容")
        return

    print(f"[Insert] 共 {len(documents)} 个文档，调用 skill.ainsert() 异步插入...")
    skill = await create_skill(args.config)
    try:
        await skill.ainsert(documents)
        print(f"\n✅ 增量插入完成")
    finally:
        await skill.finalize()


async def cmd_query(args):
    """查询命令"""
    skill = await create_skill(args.config)
    try:
        result = await skill.query(args.question, mode=args.mode)
        print(f"\n{'='*60}")
        print(f"📝 问题: {result['query']}")
        print(f"🔍 模式: {result['mode']}")
        print(f"⏱️ 耗时: {result['elapsed_time']:.2f}s")
        print(f"{'='*60}")
        print(f"\n📖 回答:\n{result['answer']}")
    finally:
        await skill.finalize()


async def main():
    parser = argparse.ArgumentParser(description="LightRAG CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # load 命令
    load_parser = subparsers.add_parser("load", help="加载文档到索引（增量式）")
    load_parser.add_argument("--data-path", required=True, help="文档目录路径")
    load_parser.add_argument("--config", help="配置文件路径")

    # backup 命令
    backup_parser = subparsers.add_parser("backup", help="备份当前索引（时间戳命名）")
    backup_parser.add_argument("--keep", type=int, default=3, help="保留最近 N 个备份 (默认: 3)")
    backup_parser.add_argument("--config", help="配置文件路径")

    # insert 命令（增量更新）
    insert_parser = subparsers.add_parser("insert", help="增量添加文档到现有索引（直接 ainsert）")
    insert_parser.add_argument("--data-path", required=True, help="文档目录路径")
    insert_parser.add_argument("--config", help="配置文件路径")

    # query 命令
    query_parser = subparsers.add_parser("query", help="查询索引")
    query_parser.add_argument("question", help="查询问题")
    query_parser.add_argument("--mode", default="hybrid",
                             choices=["naive", "local", "global", "hybrid", "mix"],
                             help="查询模式 (默认: hybrid)")
    query_parser.add_argument("--config", help="配置文件路径")

    args = parser.parse_args()

    if args.command == "load":
        await cmd_load(args)
    elif args.command == "backup":
        await cmd_backup(args)
    elif args.command == "insert":
        await cmd_insert(args)
    elif args.command == "query":
        await cmd_query(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
