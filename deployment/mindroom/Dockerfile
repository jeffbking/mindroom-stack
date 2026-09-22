# Keep the upstream application and dependencies pinned; apply only this fix.
ARG MINDROOM_BASE_IMAGE=ghcr.io/mindroom-ai/mindroom@sha256:adaf692c4e5f5bacabca66363f56d8037321f35c4d0c31153f208322a37a489c
FROM ${MINDROOM_BASE_IMAGE}
WORKDIR /app
COPY save-generation.patch /tmp/save-generation.patch
COPY test_save_generation.py /tmp/test_save_generation.py
RUN git apply --check /tmp/save-generation.patch \
    && git apply /tmp/save-generation.patch \
    && python /tmp/test_save_generation.py
