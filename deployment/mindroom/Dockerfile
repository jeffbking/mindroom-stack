# Keep the upstream application and dependencies pinned; apply the reviewed deployment patches.
ARG MINDROOM_BASE_IMAGE=ghcr.io/mindroom-ai/mindroom@sha256:adaf692c4e5f5bacabca66363f56d8037321f35c4d0c31153f208322a37a489c
FROM oven/bun:1.3.14@sha256:e10577f0db68676a7024391c6e5cb4b879ebd17188ab750cf10024a6d700e5c4 AS bun
FROM ${MINDROOM_BASE_IMAGE} AS patched
WORKDIR /app
COPY save-generation.patch /tmp/save-generation.patch
COPY agent-delete.patch /tmp/agent-delete.patch
COPY xiaomi-mimo.patch /tmp/xiaomi-mimo.patch
COPY test_xiaomi_mimo.py /tmp/test_xiaomi_mimo.py
COPY test_save_generation.py /tmp/test_save_generation.py
RUN git apply --check /tmp/save-generation.patch \
    && git apply /tmp/save-generation.patch \
    && git apply --check /tmp/agent-delete.patch \
    && git apply /tmp/agent-delete.patch \
    && git apply --check /tmp/xiaomi-mimo.patch \
    && git apply /tmp/xiaomi-mimo.patch \
    && python /tmp/test_save_generation.py \
    && python /tmp/test_xiaomi_mimo.py

FROM patched AS dashboard-build
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
WORKDIR /app/frontend
RUN bun install --frozen-lockfile \
    && bun run test:unit src/components/AgentEditor/AgentEditor.test.tsx \
       src/store/configStore.test.ts \
    && bun run build

FROM patched
COPY --from=dashboard-build --chown=1000:1000 /app/frontend/dist /app/frontend/dist
