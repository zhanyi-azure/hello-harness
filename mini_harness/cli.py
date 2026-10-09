# mini_harness/cli.py —— 命令行入口：解析参数 → 调 core.run → 打印结果
import argparse
import sys

from . import core


def main():
    parser = argparse.ArgumentParser(
        prog="mini_harness",
        description="mini agent loop：多轮工具调用问答（带权限闸门与上下文压缩）")
    parser.add_argument("question", help="你要问的问题（含空格请用引号包住）")
    parser.add_argument("--max-rounds", type=int, default=10,
                        help="大循环轮数安全阀（默认 10）")
    args = parser.parse_args()

    try:
        result = core.run(args.question, max_rounds=args.max_rounds)
    except RuntimeError as e:
        # 环境类错误（如缺 key）：库层抛 RuntimeError，入口层负责人话提示+非 0 退出码
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
