# Private MindRoom on 5900xt

Installation: `/home/jeff/Developer/mindroom-stack`.

| Service | Canonical URL | Host backend |
| --- | --- | --- |
| Matrix | https://matrix.walrus-bebop.ts.net | 127.0.0.1:8008 |
| Chat | https://mindroom.walrus-bebop.ts.net | 127.0.0.1:8240 |
| Dashboard | https://mindroom-admin.walrus-bebop.ts.net | 127.0.0.1:8765 |

Transit already owns port 8080. Only Chat's internal proxy port differs from
the requested example. No LAN address or node IP is used in browser config.
The isolated Compose network is `10.91.0.0/24`: Docker's automatic pools were
exhausted, and this subnet did not overlap the existing host routes/networks.

`origin` is https://github.com/jeffbking/mindroom-stack.git;
`upstream` is https://github.com/mindroom-ai/mindroom-stack.git.
The original stack revision was `e23ee0e` (no upstream stack release tags).
Dependencies remain upstream images, not source forks.

## Reproducible configuration

The exact Linux amd64 image digests are recorded in `deployment.env.example`
and the default image references in `../compose.override.yaml`:

| Component | Installed version | Image digest |
| --- | --- | --- |
| MindRoom | 2026.9.231 | sha256:adaf692c4e5f5bacabca66363f56d8037321f35c4d0c31153f208322a37a489c |
| mindroom-chat | v4.12.6-mindroom.78 | sha256:2c1cdaa0f6fbf1a16db7cdd4adcd285d7d0258d2b5a32bbfc3fc7ebdfda6975a |
| mindroom-tuwunel | v1.9.1-mindroom.3 | sha256:4dc1738d80156b5250879cd76bbacb2a8b0ff2db53edde4fe2a3f24e45ad2175 |

The original `.env.example`, `compose.yaml`, `config/config.yaml`, and workspace
templates stay close to upstream. `compose.override.yaml` applies the private
deployment. `deployment/config.yaml` is the reproducible initial configuration;
`runtime/config/config.yaml` is the live writable copy used by the dashboard.
Review and fold intended dashboard changes into the template before committing.
Do not blindly overwrite the runtime copy during upgrades.

The model is `muse-spark-1.3-contributor` at `https://api.meta.ai/v1` through
MindRoom's supported `openai` / `chat_completions` adapter. `META_API_KEY` in
the private `.env` is mapped to the adapter's `OPENAI_API_KEY` inside the
container. This does not configure an OpenAI-hosted model. No key is tracked.

Reuse: official Compose, MindRoom's provider adapter, Matrix registration-token
support, Tailscale Serve, and the upstream smoke-test helpers handle deployment
and protocols. The additions are deployment-specific configuration and small
extensions to the existing setup/test scripts; no protocol client, parser,
reverse proxy, or application source fork was added.

## Identity, access, and data

**Never change `matrix.walrus-bebop.ts.net` as the Matrix server name on this
database.** It was configured before any user or room was created.

Owner: `@jeff:matrix.walrus-bebop.ts.net`, created through Chat before the bots.
As the first registered human, Jeff owns the Tuwunel admin room. The initial
password and a deployment test session are in `runtime/jeff-credentials.json`
(0600, ignored). Retrieve it locally; never paste credentials into git or logs.

Managed accounts are `@mindroom_assistant`, `@mindroom_mind`,
`@mindroom_router`, and `@mindroom_user`, all on this homeserver.
The private MindRoom space contains `#lobby` and `#personal` on this server;
Tuwunel also has `#admins`. Lobby and Personal are invite-only, unlisted, and
give Jeff administrator access. Lobby contains both Assistant and Mind for
shared-room mentions; Personal contains Mind. Agent response and invitation permissions are
restricted to Jeff's full Matrix ID. Mention Assistant or Mind using Chat's
autocomplete to address the desired agent. The current upstream runtime may
also answer Jeff's unmentioned messages in its single-agent rooms; external
agent identities have no reply permission, preventing automatic bot loops.

Registration is **token-gated from first startup**, not unrestricted.
`TUWUNEL_ALLOW_REGISTRATION=true` remains necessary for dynamically provisioned
MindRoom accounts; `MATRIX_REGISTRATION_TOKEN` is passed only to MindRoom and
Tuwunel. Guest registration and federation are disabled. New humans need a
deliberate invitation and provisioning step; do not share the provisioning token.

Tailscale Services are `svc:matrix`, `svc:mindroom`, `svc:mindroom-admin`, all
HTTPS port 443. Their grants allow `autogroup:owner` and `tag:server` only;
their service advertisements auto-approve `tag:server`, following the host's
existing convention. The dashboard relies on this Tailnet access boundary;
its standalone admin UI does not have a separate Matrix login. Chat requires
Matrix authentication. Nothing uses Funnel, a public tunnel, or a LAN listener.
The managed rooms are private but not E2EE by default.

Chat hides the signup link after the initial owner account is created. Its
welcome screen links directly to the canonical dashboard. The hosted-service
"local MindRoom" pairing tab is disabled because this standalone stack does
not implement that hosted pairing API. The initial account was created with
the signup UI enabled and the private registration token; enable that UI only
temporarily when deliberately provisioning another human.

| Persistent location | Contents |
| --- | --- |
| `mindroom-stack_tuwunel_data` at `/var/lib/tuwunel` | RocksDB homeserver database, users, rooms, events, signing keys, Matrix media |
| `mindroom-stack_mindroom_data` at `/app/mindroom_data` | Matrix account credentials/state, encryption keys, sync cursors, agent sessions, memory/search indexes, control state, tracking |
| `mindroom-stack_mindroom_logs` at `/app/logs` | Application logs |
| `runtime/config/` bind mount at `/app/config` | Writable MindRoom configuration and config-adjacent files |
| `runtime/workspace/` bind mount | Mind's workspace, identity/context files and file memories |
| `.env`, `runtime/jeff-credentials.json` | Private deployment and initial human credentials |

Back up the three named volumes, both runtime bind mounts, and `.env` together.
For a simple consistent backup, stop only this stack and use standard `tar` or
your backup software on the mounted data, then start it again. Protect backups
as secrets. Never copy live RocksDB files as a supposedly consistent snapshot.
No backup scheduler was added to other host applications.
**Never use `docker compose down -v` or prune these volumes.**

## Operations

On a **fresh checkout**, before starting any containers:

```sh
cp deployment/deployment.env.example .env  # only when .env does not exist
chmod 600 .env
# Set META_API_KEY and a generated MATRIX_REGISTRATION_TOKEN privately in .env.
python3 scripts/bootstrap_runtime.py
```

Bootstrap copies the tracked deployment config and Mind workspace seeds only
when individual destination files are absent. It preserves existing live edits
and memories. Quickstart also runs it before Compose startup. For recovery,
restore the private .env, runtime files and data volumes from a consistent
backup; fresh templates are not a replacement for recovered state.

For a genuinely new homeserver, temporarily enable `auth.allowRegistration` in
`deployment/client-config.json`, start `tuwunel client` with Compose's `--no-deps`
option, configure their private Tailscale mappings, and create Jeff through Chat
using the registration token **before starting MindRoom**. This gives the human
the first-account admin role. Disable that signup UI again and restart only
`client`, then run `./scripts/quickstart.py`. Do not repeat first registration
against an existing database. If the default quickstart creates a missing .env,
it uses this deployment's template, restricts its permissions, and stops for
credential configuration.
For the private smoke test, store the owner's full `user_id` and `password` in
`runtime/jeff-credentials.json` as JSON and restrict it to mode 0600. The test
creates and logs out its own session; it does not need a saved access token.

Run in `/home/jeff/Developer/mindroom-stack`:

```sh
docker compose up -d                    # start
docker compose down                     # stop; retain named volumes
docker compose restart                  # restart with current container config
docker compose logs -f --tail=200        # logs (may contain private messages)
docker compose ps --all                  # status; permissions exits 0 normally
git rev-parse HEAD
docker compose images
docker volume ls --filter label=com.docker.compose.project=mindroom-stack
./scripts/quickstart.py --wait-only       # backend readiness; reports canonical URLs
./scripts/smoke-private.sh --restart-check
```

After changing `.env` or Compose, use `docker compose up -d` to recreate changed
containers; `restart` does not reload their environment. Runtime YAML is watched
by MindRoom. Do not publish unredacted `docker compose config` output: it expands
the provider key and registration token.

The official smoke test has two small production options: `--credentials-file`
logs in as an already invited account instead of creating an unrestricted test
account, and `--client-homeserver-url` keeps local backend probes separate from
the browser's canonical URL. It verifies both managed agents, membership,
restart persistence, and a post-restart reply. It sends visible test messages.
The temporary smoke-test login is logged out on success or failure, including
after restart checks; it does not accumulate permanent owner sessions.

To exercise the same test over canonical HTTPS, use `--canonical`:

```sh
./scripts/smoke-private.sh --canonical
curl -fsS https://matrix.walrus-bebop.ts.net/_matrix/client/versions
curl -I https://mindroom.walrus-bebop.ts.net
curl -I https://mindroom-admin.walrus-bebop.ts.net
```

Tailscale Serve mappings persist independently of Compose:

```sh
tailscale serve --service=svc:matrix --https=443 http://127.0.0.1:8008
tailscale serve --service=svc:mindroom --https=443 http://127.0.0.1:8240
tailscale serve --service=svc:mindroom-admin --https=443 http://127.0.0.1:8765
tailscale serve status
tailscale serve get-config --all
```

Never reset Serve or apply a replacement global Serve configuration.

## Deliberate upgrades and rollback

Upstream review (does not deploy or merge):

```sh
git fetch upstream
git log --oneline HEAD..upstream/main
git diff HEAD...upstream/main -- compose.yaml config scripts
git worktree add ../mindroom-stack-upgrade -b upgrade/review main
```

Review compatibility with the pinned images, then merge or rebase upstream
**in the upgrade worktree** and deliver a reviewed PR. Back up before switching
production to the approved revision. Never auto-merge upstream into production.

Container upgrade: choose a published release deliberately, then resolve it:

```sh
docker pull ghcr.io/mindroom-ai/mindroom:CHOSEN_VERSION
docker image inspect ghcr.io/mindroom-ai/mindroom:CHOSEN_VERSION \
  --format '{{json .RepoDigests}}'
```

Repeat for Chat/Tuwunel as needed. Review release notes, migrations, platform
and compatibility; update the three image variables in the private `.env`,
`deployment/deployment.env.example`, and Compose override defaults to the
reviewed digests. Commit nonsecret changes. Save the prior `.env` and an offline
data snapshot before `docker compose up -d`; run both smoke modes afterward.
No image updater or `pull_policy: always` is configured.

Rollback configuration and images only if the old binaries support the current
data schema:

```sh
docker compose stop
git switch --detach KNOWN_GOOD_COMMIT
cp /PRIVATE_BACKUP_PATH/.env .env
# Restore the corresponding runtime/config only if it changed.
docker compose up -d
./scripts/smoke-private.sh
```

If an upgrade migrated the database incompatibly, restore the complete offline
snapshot to replacement volumes and bind mounts before starting old binaries.
Keep the failed deployment's volumes for recovery; never destroy them as a
rollback shortcut. Return to `main` after the reviewed correction is ready.

## External agents (investigated, not provisioned)

### MCPHub tools for Mind

Mind connects to the existing private MCPHub endpoint
`https://mcp.walrus-bebop.ts.net/mcp/$smart` with `streamable-http`.
`$smart` is a literal gateway path segment, not an environment placeholder;
single-quote the URL if using it in a shell. The endpoint is reachable from
the MindRoom container without an additional authorization header.

The top-level `mcp_servers.smart` definition registers `mcp_smart`; Mind's
existing tool list includes it alongside `memory` and `thread_tags`. The
gateway exposes `smart_search_tools` and `smart_call_tool`, allowing discovery
and invocation of the connected MCPHub integrations. This includes their
write capabilities. Mind retains its owner-only conversation policy. Other
agents receive this access only when `mcp_smart` is added to their tool lists.

Agent self-configuration tools cannot create a top-level MCP server. Register
the server in the live `runtime/config/config.yaml` on the host, and preserve
the same definition in `deployment/config.yaml` for reproducible setup.
MindRoom reloads this configuration without a Docker restart. A server outage
uses MindRoom's default graceful degradation; it does not block agent startup.

### External Matrix identities

[`matrix-mcp`](https://github.com/mindroom-ai/matrix-mcp) 0.8.1 is the existing
MIT-licensed Python >=3.12 integration. Local stdio provides room/history reads,
thread replies, explicit Matrix mentions, membership and bounded media tools.
It does not itself wake a coding CLI whenever a room message arrives.

For a later integration, provision separate accounts (`@codex`, `@claude`,
`@hermes`, `@architect`, `@reviewer`) on this homeserver. Invite only the needed
accounts to each private room. Give each process a separate config directory
and Matrix device/token; never authenticate all agents as Jeff.
For example, using a distinct `XDG_CONFIG_HOME` for each identity:

```sh
uv tool install 'matrix-mcp==0.8.1'
XDG_CONFIG_HOME=/PRIVATE_CONFIG/codex matrix-mcp auth password \
  https://matrix.walrus-bebop.ts.net @codex:matrix.walrus-bebop.ts.net
# Use the SAME XDG_CONFIG_HOME when launching that identity's stdio server:
XDG_CONFIG_HOME=/PRIVATE_CONFIG/codex matrix-mcp serve
```

The MCP client launches this stdio process; normal operation opens no HTTP port.
Hermes can use its native Matrix adapter later. OneShot/GitDock/SDLC should use
separate accounts with explicit mention activation, self-message filtering,
event-ID deduplication and bounded dispatch. Do not enable an indiscriminate
room listener or broaden MindRoom's responder permissions as part of base setup.
No external agent credentials, MCP registrations, or dispatch daemons were added.
