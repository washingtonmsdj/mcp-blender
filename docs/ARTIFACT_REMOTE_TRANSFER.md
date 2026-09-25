# Resumable artifact reads (Agent 1.20.7)

`artifact.read_chunk` returns actual file bytes in bounded base64 chunks through
the existing job result channel. It is a fallback transfer path, not a storage
upload gateway. Each chunk requires a job round trip; use `artifact.preview`
with thumbnails for visual iteration instead of repeatedly downloading models.

The remote session must be authorized for `artifact.read_chunk`. This release
does not create grants or expand existing remote-session permissions.

## First request

Action: `artifact.read_chunk`. Payload:

```json
{
  "project": "cerco-no-interior-mvp",
  "project_artifact_path": "exports/model.glb",
  "offset": 0,
  "max_bytes": 32768
}
```

The project path is relative to its `Artifacts` directory. Alternatively use
`artifact_name` for an artifact under the Agent's project artifact directory.
The same containment checks as `artifact.preview` apply, including resolved-path
checks. Arbitrary project source files are outside these artifact roots.

## Receiver algorithm

1. Require a successful result. Capture `source_version` and `source_size_bytes`.
2. Decode `base64`, verify its length against `size_bytes`, and verify SHA256
   against `chunk_sha256`. Require the response offset to equal the requested one.
3. Write to a temporary destination at that offset. Do not append an identical
   retried chunk twice. Persist the offset only after the write succeeds.
4. If `eof` is false, request `offset=next_offset` and the same `source_version`.
   Keep the same artifact selector and project for all requests.
5. Require consistent version and total size on every response. At EOF, require
   the assembled size to equal `source_size_bytes`, then rename the temporary
   destination. An empty file returns an empty chunk with `eof=true`.
6. On `artifact_changed`, discard the partial file and restart from offset zero.
   Other failures must not be interpreted as EOF.

`source_version` hashes file identity and size/timestamps; it is a change detector,
not a full-file cryptographic digest or an immutable snapshot. Writers must finish
exports before downloading. Chunk SHA256 detects corrupt decoded chunks, while a
known full-file checksum from the export can additionally validate the assembly.

## Bounds and rollout

- Binary chunks: 1–32,768 bytes, keeping base64 plus metadata below the v2 result
  limit of 65,536 bytes for normal artifact filenames.
- Offset: integer from zero through file size. Nonzero offsets require the first
  response's version identifier.
- Memory: one bounded chunk; no whole-file read or hash for each request.
- No backend migrations or credential changes.
- This release adds the Agent capability and usage contract. A remote download
  client is not installed automatically. No end-to-end transfer or test suite
  was run as part of this implementation.
