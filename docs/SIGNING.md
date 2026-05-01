# Code Signing and Notarization

This document explains how to produce trusted macOS and Windows release artifacts for Hermes CEO Console.

## Current status

The repo supports signing/notarization in GitHub Actions when the required GitHub Secrets are configured.

Without secrets:
- macOS DMG builds unsigned or ad-hoc/development-signed depending on the runner.
- Windows EXE builds unsigned.
- Users may see Gatekeeper or SmartScreen warnings.

With secrets:
- macOS app is signed with Developer ID Application and notarized by Apple.
- Windows installer is Authenticode-signed through electron-builder using a PFX certificate.

## Required GitHub Secrets

Repo: `contentscoin/hermes-ceo-console-installer`

### macOS

| Secret | Description |
|---|---|
| `MAC_CERTIFICATE_P12_BASE64` | Base64 encoded Developer ID Application `.p12` certificate. |
| `MAC_CERTIFICATE_PASSWORD` | Password for the `.p12` certificate. |
| `APPLE_ID` | Apple Developer account email. |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password for notarization. |
| `APPLE_TEAM_ID` | Apple Developer Team ID. |

The certificate must be `Developer ID Application`, not just `Apple Development`.

Local check:

```bash
security find-identity -v -p codesigning
```

Expected identity example:

```text
Developer ID Application: Company Name (TEAMID)
```

### Windows

| Secret | Description |
|---|---|
| `WIN_CERTIFICATE_PFX_BASE64` | Base64 encoded Windows code signing `.pfx` certificate. |
| `WIN_CERTIFICATE_PASSWORD` | Password for the `.pfx` certificate. |

EV/OV code signing certificates or cloud signing providers can be used later. This alpha workflow expects a PFX file.

## Creating the macOS certificate secret

Export `Developer ID Application` certificate from Keychain Access as `.p12`, then:

```bash
base64 -i DeveloperIDApplication.p12 | pbcopy
gh secret set MAC_CERTIFICATE_P12_BASE64 --repo contentscoin/hermes-ceo-console-installer --body "$(pbpaste)"
gh secret set MAC_CERTIFICATE_PASSWORD --repo contentscoin/hermes-ceo-console-installer --body "<p12-password>"
gh secret set APPLE_ID --repo contentscoin/hermes-ceo-console-installer --body "<apple-id-email>"
gh secret set APPLE_APP_SPECIFIC_PASSWORD --repo contentscoin/hermes-ceo-console-installer --body "<app-specific-password>"
gh secret set APPLE_TEAM_ID --repo contentscoin/hermes-ceo-console-installer --body "<team-id>"
```

Do not paste these values into chat, README, issues, or logs.

## Creating the Windows certificate secret

Use a real OV/EV Windows code-signing certificate exported as `.pfx`. Do not commit or paste the PFX/password into chat.

macOS/Linux one-line pattern:

```bash
base64 -i /path/to/CodeSigningCert.pfx | tr -d '\n\r[:space:]' | gh secret set WIN_CERTIFICATE_PFX_BASE64 --repo contentscoin/hermes-ceo-console-installer
```

Then register the PFX password interactively:

```bash
gh secret set WIN_CERTIFICATE_PASSWORD --repo contentscoin/hermes-ceo-console-installer
```

Enter the password locally, press Enter, then Ctrl+D.

Windows PowerShell pattern:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("CodeSigningCert.pfx")) | gh secret set WIN_CERTIFICATE_PFX_BASE64 --repo contentscoin/hermes-ceo-console-installer
```

Then:

```powershell
gh secret set WIN_CERTIFICATE_PASSWORD --repo contentscoin/hermes-ceo-console-installer
```

## Running a signed build

After secrets are set:

```bash
gh workflow run release.yml --repo contentscoin/hermes-ceo-console-installer --ref main
```

Or push a tag:

```bash
git tag v0.1.0-alpha.2
git push origin v0.1.0-alpha.2
```

## Verification

### macOS

```bash
codesign --verify --deep --strict --verbose=2 "Hermes CEO Console.app"
spctl -a -vv "Hermes CEO Console.app"
xcrun stapler validate "Hermes CEO Console.app"
```

For DMG:

```bash
spctl -a -t open --context context:primary-signature -vv "Hermes CEO Console-*.dmg"
```

### Windows

On Windows PowerShell:

```powershell
Get-AuthenticodeSignature ".\Hermes CEO Console Setup *.exe" | Format-List
```

Expected `Status: Valid`.

## Security rules

- Do not commit `.p12`, `.pfx`, passwords, provisioning profiles, or exported keychain files.
- Rotate secrets if a certificate is exposed.
- Keep the installer secret-free; user Telegram/Paperclip/Codex credentials remain local.
- Paperclip writes and Telegram sends remain explicit approval-gated even after signed installer distribution.
