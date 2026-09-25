# Component versioning

OrdaX does **not** use one global version for every component.

Different surfaces change at different rates and have different compatibility
meanings, so each one owns a separate version.

## Current version domains

| Component | Version | Meaning |
| --- | --- | --- |
| `mcp-blender-unity` distribution / bridge | `0.3.0` | Python package and local Blender/Unity bridge release line |
| OrdaX Device Agent | `1.22.0` | Typed local capability runtime, orchestration and update planning |
| Blender Live protocol | `9` | IPC compatibility contract between host bridge and visible Blender companion |
| Blender companion bundle format | `1` | Manifest/fingerprint format for the multi-file Blender runtime bundle |
| Reference Contract | `1` | Project-local visual-reference manifest schema |

These numbers are intentionally independent. A Device Agent patch does not imply a
Blender protocol change. A Reference Contract schema bump does not imply a bridge
package release unless packaging/runtime code also changes.

## Compatibility rules

- Bump the **bridge package** when the installable `mcp-blender-unity`
  distribution changes in a release-significant way.
- Bump the **Device Agent** for agent actions, orchestration, validation, control
  plane behavior or packaged runtime behavior.
- Bump the **Blender Live protocol** only for an IPC compatibility change that
  requires host/companion agreement.
- Bump the **companion bundle format** only when the manifest/fingerprint format
  changes, not merely when files inside the bundle change.
- Bump the **Reference Contract** only when its manifest schema changes
  incompatibly or gains semantics that require explicit schema negotiation.

## Runtime visibility

`agent.status` exposes a `versions` object containing all of these domains.
It also exposes `capability_contracts`, a separate runtime view of typed feature availability. Version numbers and capability availability are related but not interchangeable diagnostics.
This is the canonical runtime inventory for diagnostics and update decisions.

The installable distribution version in `pyproject.toml` must match
`mcp_blender_unity.__version__`. CI tests enforce that invariant.

Do not copy the Device Agent version into every app/module just to make the numbers
look synchronized. Components should advance only when their own contract or
implementation changes.

The Device Agent now also publishes `ordax.device-agent-components/1`. Adapter
identities (Blender, Unity, Git, MCP interface and CLI bridge) have independent
versions/failure domains. In Owner/Development they are still delivered by Git
main for speed; this does not mean the whole OS is reinstalled. Production
independent activation remains gated on signed component slots with health,
promotion and rollback. See [COMPONENT-UPDATES.md](COMPONENT-UPDATES.md).
