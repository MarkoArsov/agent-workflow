# Build locally, then install reviewed provider CLIs and the project's check tools.
# Pin your chosen base and harness versions for a reproducible production image.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Install the selected harnesses using their official installation instructions.
# Add their prerequisites (such as Node/npm), then the exact reviewed CLI versions.
# Add project toolchains (such as a compiler or SDK) needed by your named checks.
# Do not COPY credentials, host configuration, repositories or plovi evidence.
# Preflight runs each selected harness --help; the minimal image alone cannot run agents.
WORKDIR /tmp
