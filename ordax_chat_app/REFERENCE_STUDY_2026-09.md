# Reference study — regular ChatGPT as a development agent

Date: 2026-09-30

## OpenChatX

Reference: https://github.com/XiaoPuOuO/openchatx-mcp

Useful ideas:
- regular ChatGPT remains the model/planner;
- official MCP + OpenAI Secure MCP Tunnel instead of browser-session reverse engineering;
- coding-grade filesystem and shell;
- computer control;
- MCP aggregation;
- Skills, Rules, Projects, Tasks and Toolboxes;
- cross-session summaries;
- optional subagents;
- lazy capability discovery to keep tool context small.

Risk called out by the project itself: local tools run with the OS user's permissions.

## Chat On Steroids

Reference discussion:
https://www.reddit.com/r/mcp/comments/1vvjib3/i_built_a_windows_mcp_connector_that_gives/

Useful ideas:
- Codex-style local tool surface from normal ChatGPT;
- local files and terminal;
- computer use;
- compaction;
- parallel worker chats/subagents via a browser extension.

The browser-extension approach is useful as a compatibility layer for ChatGPT-side orchestration, but it should not be the authority for local-device permissions.

## OpenAI official MCP/App path

References:
- https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt
- https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk

Relevant constraints:
- ChatGPT connects to remote MCP servers, not directly to localhost;
- Secure MCP Tunnel is the supported path for a private/local developer machine;
- custom MCP apps can expose write/modify actions on supported plans;
- risky write actions may require confirmation or be blocked by the client;
- the server owner remains responsible for MCP safety.

## ORDAX design choice

We will not clone any one project. The target combines:
1. developer-grade filesystem, terminal and Git;
2. process/preview lifecycle;
3. computer/browser control;
4. project Rules/Skills and resumable context;
5. subagents and MCP aggregation;
6. specialized adapters such as Blender and Unity;
7. existing ORDAX device identity, outbound agent connection, grants, audit and revocation.

The key distinction is that capability is broad, but authority is explicit. A file grant does not silently imply terminal or computer control. Once terminal is granted, however, it is a real development terminal rather than a fake subset.
