# test_mcp_client.py —— 用 MCP 客户端连接 mcp_demo.py，体验一次"宿主"视角
#
# 在 mini_loop 里，"看菜单 → 开单"的是【模型】；
# 在 MCP 的世界里，看菜单 → 调工具的是【宿主】（Claude Code、Cursor……）。
# 本脚本就客串一次宿主：连接服务器 → initialize 握手 → 看菜单 → 点菜。
#
# stdio 传输的含义：stdio_client 会把 mcp_demo.py 作为子进程启动，
# 通过它的标准输入/输出收发 MCP 协议消息——宿主和服务器就这样隔空对话。
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # 服务器启动参数：用【当前这颗 .venv 的 python】启动 mcp_demo.py
    # （sys.executable = 正在运行本脚本的 python，保证两边用的是同一个 mcp 库）
    params = StdioServerParameters(command=sys.executable, args=["mcp_demo.py"])

    async with stdio_client(params) as (read, write):
        # ClientSession 负责协议的握手与消息收发
        async with ClientSession(read, write) as session:
            # initialize：握手报家门，协商协议版本与双方能力
            await session.initialize()
            print("已连接 mini-harness 服务器，握手成功")

            # list_tools：宿主视角的"看菜单"——
            # 菜单内容由 mcp_demo.py 里的 @mcp.tool() 自动生成
            tools = await session.list_tools()
            print(f"服务器共有 {len(tools.tools)} 个工具：")
            for t in tools.tools:
                desc = (t.description or "").strip().splitlines()[0]
                print(f"  - {t.name}：{desc}")

            # call_tool：宿主视角的"点菜"——让服务器执行 read_file
            # 注意：真正干活的函数跑在【服务器进程】里，宿主只拿到文字结果
            print("\n调用 read_file(path='README.md')，返回前 80 字符：")
            result = await session.call_tool("read_file", {"path": "README.md"})
            print(result.content[0].text[:80])


asyncio.run(main())
