"""Exercise the repository's real stdio MCP transport against the Salvador scene."""
import asyncio,json,sys,os
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params=StdioServerParameters(command=sys.executable,args=['-m','mcp_blender_unity.server'],env=dict(os.environ))
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            result=await session.call_tool('blender_run_python',{'script_path':str(Path(sys.argv[1]).resolve()),'blend_file':str(Path(sys.argv[2]).resolve()),'timeout_seconds':300})
            for item in result.content:
                if getattr(item,'text',None):print(item.text)
            if result.isError:raise SystemExit(1)
            for item in result.content:
                if getattr(item,'text',None):
                    try:data=json.loads(item.text)
                    except ValueError:continue
                    if data.get('ok') is False:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
