# mcp_demo.py —— 把 mini_loop 的两个工具包装成最小 MCP server（stdio 传输）
#
# MCP（Model Context Protocol）是什么？
#   一个开放协议：把"工具怎么登记、怎么被发现、怎么被调用"标准化，
#   让任何 MCP 宿主（Claude Code、Cursor……）都能即插即用地接入你的工具。
#
# 与 mini_loop 的对照（本课灵魂）：
#   mini_loop 里你要【手工】维护两样东西——
#     TOOLS_SCHEMA（发给模型的说明书）+ TOOL_FUNCS（名字→函数的注册表）
#   而这里一个装饰器 @mcp.tool() 就全包了：
#     它读取函数的类型注解（path: str）和 docstring（"读取指定路径的…"），
#     自动生成说明书（JSON Schema），同时把函数登记进注册表。
#   【MCP 没有发明新思想，它把 mini_loop 的手工动作标准化了】。
import os
from mcp.server.fastmcp import FastMCP

# 给服务器起名：宿主连接握手时会看到它
mcp = FastMCP("mini-harness")


@mcp.tool()
def read_file(path: str) -> str:
    """读取指定路径的文本文件内容"""
    # 实现逻辑与 mini_loop 完全相同（含错误自愈设计）
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 {path} 不存在"
    except IsADirectoryError:
        # 错误是数据：告诉模型正确的工具是谁，它下一轮自己换
        return f"错误：{path} 是一个目录，不是文件。要看目录内容请改用 list_dir 工具"


@mcp.tool()
def list_dir(path: str = ".") -> str:
    """列出目录下的文件与文件夹名"""
    try:
        return "\n".join(os.listdir(path))
    except FileNotFoundError:
        return f"错误：目录 {path} 不存在"


# stdio 传输：本脚本作为子进程被宿主启动，
# 宿主通过它的标准输入/输出（stdin/stdout）收发 MCP 协议消息。
# 只在直接运行本文件时才启动服务器（被 import 时不启动）。
if __name__ == "__main__":
    mcp.run()
