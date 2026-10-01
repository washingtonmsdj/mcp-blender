# ORDAX Chat App

ORDAX Dev turns regular ChatGPT into a development agent connected to the user's computer through the official MCP/plugin path.

## Primary mode — regular ChatGPT

Regular ChatGPT is the default brain and planner:

```text
ChatGPT regular chat
  -> ORDAX plugin / remote MCP
  -> ORDAX Control Plane
  -> persistent Device Agent connection
  -> local runtime
       -> projects / files
       -> terminal / Git
       -> processes / preview
       -> browser / computer control
       -> Blender / Unity / adapters
```

This mode is intentionally separate from Sign in with ChatGPT inference. The ORDAX desktop is the runtime/dashboard; the conversation remains hosted by ChatGPT so it uses the normal ChatGPT chat allowance rather than the Work/Codex allowance, subject to the capabilities OpenAI enables for the user's plan and plugin/app.

Production MCP endpoint:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`

The ChatGPT distribution adapter is versioned in `plugins/ordax-studio/`.

## Optional mode — Agent / Responses

ORDAX also supports an embedded model session using **Continue with ChatGPT** and the Responses API.

This mode is useful for headless automation, autonomous workers and background execution, but OpenAI accounts its inference against the applicable Work/Codex usage pool. The UI must label this explicitly. It is not the default mode.

## Important product boundary

There is no supported API that lets a third-party desktop embed the consumer ChatGPT conversation while consuming the normal chat allowance as if it were the ChatGPT UI. ORDAX therefore does not scrape ChatGPT cookies, reverse-engineer private endpoints or automate extraction of ChatGPT output.

For normal-chat quota, ChatGPT remains the host and calls ORDAX over MCP.

For unattended 24/7 model execution, ORDAX uses an explicitly configured provider (Responses/API/other model/local model). Background automation does not impersonate normal ChatGPT conversations.

## Runtime capabilities

- project-scoped filesystem;
- terminal and Git;
- persistent processes;
- preview and browser control;
- optional computer control grants;
- Blender/Unity adapters;
- persistent agent/goal/session/checkpoint state;
- Prime/worker orchestration;
- crash-safe work queue;
- Rules, Skills and AGENTS.md context.

Blender is one adapter. ORDAX Dev is not a Blender-only MCP.
