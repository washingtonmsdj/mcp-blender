# Unity animation validation ladder

OrdaX validates Unity character animation in separate stages. A successful FBX import is not proof that the imported clip changes the character pose, and a successful Editor sample is not proof that an Animator applies root motion in Play Mode.

## 1. Deterministic ModelImporter configuration

Use:

```text
game_assets.unity_character_import_configure
```

The action requires `confirm=true` because it changes Unity import metadata and performs `SaveAndReimport`. It configures only the requested project-local model and does not install a global `AssetPostprocessor`.

Supported controls include animation type, Avatar setup, explicit `CopyFromOther` source Avatar, animation import, `optimizeGameObjects`, curve resampling and mesh readability. Controlled settings are snapshotted before reimport and OrdaX attempts rollback if reimport fails or Unity normalizes the resulting importer outside the requested contract.

## 2. Imported semantic evidence

Use:

```text
game_assets.unity_semantic_audit
```

The advanced semantic pass can prove valid/humanoid Avatar evidence, mapped humanoid bones, animation clips, root/motion curves, humanoid motion, SkinnedMeshRenderer presence and LOD renderer assignments. These are facts reported by Unity's imported assets; they do not prove that a clip actually changes a pose.

## 3. Isolated Editor pose sampling

Use:

```text
game_assets.unity_animation_sample_audit
```

The action installs a separate read-only `OrdaXGameAssetAnimationAgent.cs` companion. It refuses to run if the Editor is already in `AnimationMode`, so it does not take over a user's active animation-preview state.

For each audit it:

1. resolves a project-local imported model and an exact AnimationClip;
2. requires an explicit clip name when the model exposes multiple non-preview clips;
3. creates a Unity preview Scene rather than touching an open user Scene;
4. instantiates the model only inside that preview Scene;
5. enters `AnimationMode` and samples the clip at time zero and at a bounded normalized sample time;
6. compares local position, rotation and scale for every Transform;
7. compares every SkinnedMeshRenderer blend-shape weight;
8. reports changed Transform/blend-shape counts and maximum deltas;
9. reports clip metadata such as `humanMotion`, root curves, motion curves and generic root transform;
10. stops AnimationMode, destroys the temporary clone and closes the preview Scene in `finally`.

The default gate requires the sample to change at least one Transform or blend-shape channel. Optional requirements can enforce minimum changed Transform/blend-shape counts, humanoid motion, and root-or-motion-curve evidence.

A successful result means:

```text
editor_sample_validated = true
pose_change_validated = true
play_mode_validated = false
root_motion_application_validated = false
```

This distinction is deliberate. `AnimationMode.SampleAnimationClip` proves that Unity can evaluate the imported clip against the imported model in the Editor. It does not prove that a runtime Animator controller, transitions, layers, masks, update mode or `applyRootMotion` configuration behaves correctly.

## 4. Next gate: Play Mode animation/root motion

The next runtime gate should create an isolated, disposable playback harness and prove at runtime that:

- an Animator can bind the imported Avatar and clip;
- the sampled character deforms over multiple frames;
- no Animator/runtime errors are produced;
- when root motion is explicitly required, `Animator.hasRootMotion` and runtime motion deltas are observed with a controlled `applyRootMotion` policy;
- the temporary harness is removed without modifying canonical scenes or source assets.

That future gate must remain separate from the Editor sampler so OrdaX never reports runtime validation from import or preview evidence alone.
