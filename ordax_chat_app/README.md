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

The **normal ChatGPT allowance is never consumed through browser scraping or synthetic prompt submission**. In normal-chat mode, ChatGPT remains the conversation host and ORDAX is the MCP capability/runtime.

ORDAX Dev may show project state, Web Bridge health and Handoff controls beside that workflow, but it does not programmatically read ChatGPT output or send hidden prompts to the consumer website. The embedded ORDAX chat is reserved for providers with an explicit inference API/session contract (Responses, other providers or local models).


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


## Cross-chat Handoff

Regular ChatGPT conversations can continue across fresh chats without scraping the prior chat.

1. The current conversation calls `handoff_create` through ORDAX MCP with a compact summary, next action, changed paths and blockers.
2. ORDAX stores an opaque `hof_...` record locally with a bounded TTL.
3. A fresh ChatGPT conversation calls `handoff_get` with that ID and resumes from the returned project state.
4. The desktop also exposes a local Handoff fallback in case a ChatGPT plan does not allow the write tool.

Handoffs are project-scoped and expire automatically; they are not a hidden copy of the entire ChatGPT transcript.
