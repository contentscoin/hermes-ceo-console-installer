# NOTICE / Attribution

Hermes CEO Console Installer Pack is an FMG integration and distribution wrapper. It installs or launches local components from upstream/open-source projects and FMG-maintained forks. It is not the official distribution channel for those upstream projects unless explicitly stated by their maintainers.

## Primary upstream projects and sources

- Hermes Agent
  - Source: https://github.com/NousResearch/hermes-agent
  - Role in this pack: local AI agent CLI/runtime, profiles, tool execution, gateway support, and setup commands.
  - Ownership/licensing: belongs to Nous Research and its contributors under the license published in that repository.

- Hermes WebUI / CEO Console WebUI
  - FMG distribution source: https://github.com/contentscoin/hermes-for-web.git
  - Role in this pack: local browser UI at http://127.0.0.1:8788, workspace/artifact/profile/multi-agent/Paperclip/OpenCrab integration surfaces.
  - This installer pins a specific FMG WebUI commit in installer.manifest.json and setup scripts. Judge freshness by the WebUI repo/commit, not only by `hermes --version`.

- Paperclip
  - FMG distribution source used by this installer: https://github.com/contentscoin/paperclip.git
  - Role in this pack: local Paperclip board/service at http://127.0.0.1:3100, iframe integration, and read-only workflow diagnostics.
  - Paperclip reflection/mutations remain approval-gated and are not performed automatically by this installer.

- OpenCrab
  - Service/site: https://opencrab.sh
  - Role in this pack: optional user-configured ontology/MCP connector. This repository does not include OpenCrab endpoint keys or credentials.
  - Required display rule: redact endpoint secrets, e.g. `https://opencrab.sh/api/mcp/[REDACTED]`.

- Electron and electron-builder ecosystem
  - Sources: https://www.electronjs.org/ and https://www.electron.build/
  - Role in this pack: desktop shell, macOS DMG, and Windows NSIS installer builds.

- Windows WSL2 / Ubuntu / Node.js / pnpm
  - Sources: Microsoft WSL documentation, Ubuntu distribution packages, Node.js, and pnpm.
  - Role in this pack: Windows runtime bootstrap and JavaScript dependency management.

## FMG-authored integration layer

FMG-authored files in this repository include the installer manifest, macOS/Windows installation scripts, first-run wizard, Electron wrapper glue, FMG profile template, and operational documentation. These files are distributed under this repository's LICENSE unless a file states otherwise.

## Secret and credential policy

This repository and its release assets must not contain:

- API keys or model provider credentials
- Telegram bot tokens
- Paperclip tokens or private company secrets
- Codex OAuth/device credentials
- OpenCrab MCP endpoint keys
- Private keys, certificates, or signing credentials

Users configure credentials locally through Hermes setup, local `.env` files, OAuth/device login, or the relevant service UI.

## Trademark / affiliation note

Project names, product names, and service names remain the property of their respective owners. Mentioning them here is for compatibility, attribution, and installation guidance. This FMG installer does not imply endorsement by Nous Research, Paperclip, OpenCrab, Electron, Microsoft, Ubuntu, Node.js, or pnpm maintainers.
