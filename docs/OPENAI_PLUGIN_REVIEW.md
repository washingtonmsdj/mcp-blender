# ORDAX Dev — OpenAI plugin review runbook

Status: pre-submission checklist for ORDAX Dev 0.4.1.

## Scope

This runbook covers only the public-review path for the ORDAX Dev ChatGPT plugin. It does not change the ORDAX account model, Cloudflare Control Plane, local Runtime authority or Git provider credentials.

Canonical flow:

```text
ChatGPT
  -> ORDAX Dev plugin
  -> Cloudflare remote MCP
  -> grant enforcement
  -> ORDAX Runtime on the connected PC
  -> explicitly granted project/tool
```

GitHub remains an optional project provider. It is not the identity provider, it is not the device-enrollment authority, and it is not the bridge between ChatGPT and ORDAX Dev. New devices are enrolled by an authenticated ORDAX Product account.

## Preconditions

Before recording or submitting:

- `main` Bridge CI is green.
- Cloudflare production deploy is green.
- `/.well-known/oauth-protected-resource` advertises `openid`, `email` and `offline_access`.
- Supabase OAuth 2.1 Server is enabled for the ORDAX project.
- OAuth discovery is available at `https://<project-ref>.supabase.co/.well-known/oauth-authorization-server/auth/v1`.
- discovery advertises `offline_access`, refresh-token support, HTTPS authorization/token/registration endpoints, PKCE `S256`, and a token endpoint authentication method.
- dynamic client registration is enabled so ChatGPT can register the MCP OAuth client automatically.
- unauthenticated `/mcp` returns 401 with protected-resource metadata challenge.
- ORDAX Runtime is online on the review computer.
- only the isolated `ordax-review-demo` project is granted to the review account.
- the review account has no MFA/SMS/secondary email step that blocks a reviewer.
- `terminal.exec` is NOT granted to the review account.
- no personal or production project data appears in the review grant.

## Canonical submission path

Use the OpenAI submission flow **With MCP** and submit the production HTTPS endpoint directly:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`

The public ZIP remains the canonical portable plugin package. Registered-app mappings are for local/workspace packaging; the public MCP-backed submission uses the production endpoint in the dashboard.

## Canonical submission package

Do not build the review ZIP manually.

Use the GitHub Actions workflow `.github/workflows/plugin-review-package.yml` on the verified `main` revision and download the artifact:

`ordax-dev-plugin-review-package`

The artifact contains only:
- `ordax-dev-plugin-0.4.1.zip`;
- its matching `.sha256` file.

Verify the published SHA-256 before uploading the ZIP to the OpenAI submission UI. The workflow also rejects unexpected files inside the ZIP.

## Review account

Create a dedicated ORDAX review account in the configured identity provider.

Do not store its password in Git, plugin.json, CI logs, issues or documentation.

The account should:
- have a confirmed email;
- be usable with ordinary email/password login;
- have access only to the review device/project grants;
- remain valid for the review period;
- be revoked or rotated after review if no longer needed.

Record the username/password only in the private reviewer credential fields supplied by the OpenAI submission UI.

## Provision the review grant

After the dedicated review account connects the review computer and creates a Product device link, copy only that link UUID into the GitHub Actions workflow:

`Provision OpenAI Review Grant`

The workflow uses the protected `cloudflare-v3` Environment and its existing `ORDAX_OPERATOR_TOKEN`. Do not copy the operator token into chat, issue comments or workflow inputs.

The grant is intentionally fixed to:
- project: `ordax-review-demo`;
- actions: `projects.list`, `project.text_read`, `project.search_text`, `project.text_write`, `git.status`;
- expiry: 30 days;
- terminal access: not granted.

If the reviewer account or device link changes, provision a new review grant from the new link rather than editing D1 directly.

## Review project

Canonical project slug:

`ordax-review-demo`

Expected safe files:

- `README.md` containing `REVIEW_MARKER`;
- `sample.py`;
- optional `review-output.txt` created during the write test.

No secret, token, production file, personal document or unrelated repository should exist inside this fixture.

## Positive review prompts

Record and test these in a fresh ChatGPT conversation with only the ORDAX Dev plugin needed for the scenario:

1. `Show the projects available on my connected ORDAX computer.`
   - Expected tools: `ordax_targets`, `projects_list`.
   - Expected result: only the connected review device and granted review project are visible.

2. `Read README.md from the ordax-review-demo project.`
   - Expected tool: `project_text_read`.
   - Expected result: README content from the granted project only.

3. `Search ordax-review-demo for the phrase REVIEW_MARKER.`
   - Expected tool: `project_search`.
   - Expected result: bounded matches from the granted project.

4. `Create review-output.txt in ordax-review-demo containing the text plugin review write test.`
   - Expected tool: `project_text_write`.
   - Expected result: only the requested file is created inside the granted project.

5. `Show Git status for ordax-review-demo.`
   - Expected tool: `git_status`.
   - Expected result: bounded Git status shows `review-output.txt` as uncommitted.

## Negative review prompts

Demonstrate at least the following fail-closed cases:

1. `Read secrets.txt from a project named private-project-that-is-not-granted.`
   - Expected: access denied / project not granted.

2. `Run a terminal command in ordax-review-demo that prints the current environment variables.`
   - Expected: denied because the review account does not have `terminal.exec`.

3. `Transfer $100 to another bank account for me.`
   - Expected: ORDAX Dev is not selected as a relevant capability.

## Demo recording

The recording submitted for review should show, in one continuous sequence where practical:

1. the ORDAX Dev Runtime online on the review PC;
2. a fresh ChatGPT conversation;
3. connecting/authenticating the ORDAX Dev plugin with the dedicated review account;
4. one read-only operation;
5. one project search;
6. one bounded write operation;
7. Git status reflecting the write;
8. one unauthorized-project denial;
9. one terminal-grant denial.

Do not show:
- private user credentials;
- personal projects;
- production API keys;
- GitHub access tokens;
- Cloudflare operator secrets;
- Supabase secret/service-role keys.

Upload the recording to a stable HTTPS URL reachable by the reviewer without authentication. Once the URL exists, add it to the plugin review metadata as `demo_recording_url`.

## Domain verification

The Worker route is:

`/.well-known/openai-apps-challenge`

It intentionally returns 404 until the submission process provides the real OpenAI challenge value.

When OpenAI supplies the challenge:
1. store it as the Worker secret/config value `OPENAI_APPS_CHALLENGE`;
2. redeploy through the canonical Cloudflare workflow;
3. verify the well-known route returns HTTP 200 with the exact challenge and no surrounding JSON;
4. complete domain verification in the OpenAI UI;
5. do not commit the challenge value to Git.

## OAuth readiness check

Run this before recording or submitting:

```bash
python scripts/cloudflare/verify_product_oauth_server.py \
  https://eobcxuyvhkvdmkbaihwh.supabase.co/auth/v1
```

A 404 from the discovery endpoint means the Supabase OAuth 2.1 Server is not enabled yet. Enable it in **Authentication → OAuth Server** and enable dynamic client registration before continuing.

For the public ORDAX plugin, set **Authentication → URL Configuration → Site URL** to `https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev` and keep **Authorization Path** as `/oauth/consent`. Supabase composes those values to reach the canonical consent UI at `https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/oauth/consent`. Do not leave the Site URL pointed at the retired Vercel engineering hub.

## Submission blockers

Do not submit while any of these is true:

- Bridge CI or production Cloudflare deploy is red;
- review credentials are missing or require an additional interactive verification step;
- `demo_recording_url` is missing;
- domain challenge has not been issued/verified when the portal requires it;
- privacy policy is inconsistent with implemented retention;
- the review grant exposes real projects or terminal access unnecessarily.

## After approval

- keep the public MCP endpoint stable;
- version tool/schema changes deliberately;
- rotate review credentials if they are no longer needed;
- retain review fixture only if it remains isolated;
- continue enforcing device + project + action grants for every remote mutation.
