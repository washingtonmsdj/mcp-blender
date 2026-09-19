# Unity first-party intelligence in OrdaX

OrdaX does not depend on Codex, Claude, Grok, or Unity's third-party-agent plugin at runtime.

Instead, OrdaX uses Unity's public first-party agent-skill catalog as a capability map and implements its own typed MCP/Dev-Agent operations.

## Source of truth

- Unity docs: https://docs.unity.com/en-us/ai/unity-plugin/about-unity-plugin
- Unity public repository: https://github.com/Unity-Technologies/unity-agent-plugin

The OrdaX repository stores only capability metadata, package signals and source references. It does not vendor Unity skill bodies.

## Native OrdaX actions

### unity.project_profile

Reads the registered local Unity project and reports:

- Editor version
- Unity major version / Unity 6 compatibility
- package manifest
- render pipeline (URP, HDRP, built-in/unknown)
- scene inventory
- basic project-layout health

### unity.capabilities

Combines the project profile with Unity's public skill/capability map and reports which domains are currently applicable.

Examples:

- physics 3D
- AI Navigation
- UI Toolkit / uGUI / IMGUI
- localization
- 2D / sprites / tilemaps
- audio
- URP / Render Graph / Shader Graph
- multiplayer / Vivox
- live services
- IAP / LevelPlay
- package management / Unity CLI

Package-specific capabilities are activated from actual `Packages/manifest.json` signals instead of guesses.

### unity.skill_catalog

Returns the known first-party capability catalog and source links. This is metadata only; it does not require the Unity agent plugin to be installed.

## Execution model

The capability layer answers **what Unity-specific workflow applies**.

Typed OrdaX actions remain responsible for **doing and verifying the work**:

1. inspect project/profile/capabilities;
2. make controlled project changes;
3. refresh/compile in the real Unity Editor;
4. run project validation;
5. capture visual output when relevant;
6. fix until green.

## Security

The Unity action namespace remains allow-listed. No arbitrary remote shell is added.

The long-term direction is to turn high-value domains from the first-party catalog into dedicated typed operations, for example:

- `unity.physics_audit`
- `unity.urp_audit`
- `unity.ui_audit`
- `unity.navigation_audit`
- `unity.package_plan`
- `unity.scene_summary`

Each operation must remain deterministic, inspectable and testable.
