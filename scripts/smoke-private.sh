#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
homeserver=http://127.0.0.1:8008
client=http://127.0.0.1:8240
dashboard=http://127.0.0.1:8765
if [ "${1:-}" = --canonical ]; then
  shift
  homeserver=https://matrix.walrus-bebop.ts.net
  client=https://mindroom.walrus-bebop.ts.net
  dashboard=https://mindroom-admin.walrus-bebop.ts.net
fi
exec python3 scripts/stack_smoke_test.py \
  --homeserver "$homeserver" --client-url "$client" --dashboard-url "$dashboard" \
  --client-homeserver-url https://matrix.walrus-bebop.ts.net \
  --assistant-room-alias '#lobby:matrix.walrus-bebop.ts.net' \
  --mind-room-alias '#personal:matrix.walrus-bebop.ts.net' \
  --assistant-user-id '@mindroom_assistant:matrix.walrus-bebop.ts.net' \
  --mind-user-id '@mindroom_mind:matrix.walrus-bebop.ts.net' \
  --credentials-file runtime/jeff-credentials.json "$@"
