# test_mcp_client.py —— 用 MCP 客户端连接 mcp_demo.py，体验一次"宿主"视角
#
# 在 mini_loop 里，"看菜单 → 开单"的是【模型】；
# 在 MCP 的世界里，看菜单 → 调工具的是【宿主】（Claude Code、Cursor……）。
# 本脚本就客串一次宿主：连接服务器 → initialize 握手 → 看菜单 → 点菜。
#
# stdio 传输的含义：stdio_client 会把 mcp_demo.py 作为子进程启动，
# 通过它的标准输入/输出收发 MCP 协议消息——宿主和服务器就这样隔空对话。
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # 服务器启动参数（v2 修复）：解释器和脚本全部写【绝对路径】，不赌 PATH、不赌 cwd。
    #
    # 病根回顾——stdio 模式下，宿主用 command 指定的解释器去【启动一个子进程】，
    # 这个子进程的环境完全是隐式的，两处最容易翻车：
    # ① 裸 "python" 在 Windows 上按 PATH 找到的多半是全局 Python——
    #    它没装 mcp 包，server 一启动就 ModuleNotFoundError 秒退；
    #    宿主还傻等 initialize 握手 → 对端进程已关闭 → McpError: Connection closed。
    # ② args 用相对路径 "mcp_demo.py" 时，子进程按【继承的工作目录】找脚本，
    #    换个目录启动客户端，server 同样秒退，症状一模一样。
    #
    # 所以 harness 工程的铁律：凡是"拉起另一个进程"，解释器、脚本、工作目录
    # 全部显式指定——确定性优先，"在我电脑上能跑"不算数。
    params = StdioServerParameters(
        command=r"D:\likeme\hello-harness\.venv\Scripts\python.exe",
        args=[r"D:\likeme\hello-harness\mcp_demo.py"],
    )

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
