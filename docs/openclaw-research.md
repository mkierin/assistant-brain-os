# OpenClaw Research Report

## What is OpenClaw?

OpenClaw is a **free, open-source autonomous AI agent / personal AI assistant** created by Austrian software engineer Peter Steinberger (founder of PSPDFKit). It began as a weekend project in November 2025 and has since become one of the fastest-growing repositories in GitHub history, surpassing **165,000+ GitHub stars** as of February 2026.

**Naming history:** The project was originally called Clawdbot (a pun on "Claude" + claw), but Anthropic's legal team requested a name change. It was briefly renamed Moltbot (referencing how lobsters molt/shed their shells), before settling on its current name, OpenClaw.

**What it does:**
- Runs locally on your own machine (macOS, Linux, Windows via WSL2)
- Connects to messaging platforms: WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Microsoft Teams, Google Chat, Matrix, and more
- Can execute shell commands, read/write files, manage your filesystem, and perform web automation
- Supports 100+ preconfigured "AgentSkills" and a public registry of 3,000+ community-built skills
- Remembers context across conversations
- Completely model-agnostic -- bring your own API key or run local models

GitHub: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)

---

## Installation (Easiest & Safest)

### Prerequisites
- Node.js version 22 or higher
- macOS, Linux, or Windows (via WSL2)

### macOS / Linux
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
openclaw onboard --install-daemon
```

### Windows (PowerShell)
```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
openclaw onboard --install-daemon
```

### Alternative: Manual npm Install
```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

### Post-Installation Verification
```bash
openclaw doctor    # Run health check
openclaw status    # Check system status
openclaw dashboard # Access the web dashboard
```

The `--install-daemon` flag installs a system daemon (launchd on macOS, systemd on Linux) so the OpenClaw gateway stays running in the background.

The onboarding wizard walks you through configuring your AI provider (API key), workspace, gateway settings, and connecting messaging channels.

---

## Supported LLM APIs / Model Providers

OpenClaw is model-agnostic and supports 14+ providers:

| Provider | Auth Method | Example Model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `openai/gpt-5.1-codex` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic/claude-opus-4-6` |
| Google Gemini | `GEMINI_API_KEY` | `google/gemini-3-pro-preview` |
| Google Vertex AI | gcloud ADC | (various) |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4-5` |
| xAI (Grok) | `XAI_API_KEY` | -- |
| Groq | `GROQ_API_KEY` | -- |
| Cerebras | `CEREBRAS_API_KEY` | -- |
| Mistral | `MISTRAL_API_KEY` | -- |
| GitHub Copilot | `GITHUB_TOKEN` | -- |
| Z.AI (GLM) | `ZAI_API_KEY` | `zai/glm-4.7` |
| Vercel AI Gateway | `AI_GATEWAY_API_KEY` | -- |
| OpenCode Zen | `OPENCODE_API_KEY` | -- |

Additional providers via custom configuration: Moonshot/Kimi, Qwen, MiniMax, Synthetic, and local runtimes including Ollama, LM Studio, vLLM, and LiteLLM.

OpenRouter acts as a meta-provider, giving access to hundreds of models through a single API key. OpenClaw has built-in first-class support for it.

Models are referenced using `provider/model` syntax (e.g., `anthropic/claude-opus-4-6`), and you can switch models on the fly with `/model` commands.

---

## Best LLM for Cheap but Good Results

### Free Tier ($0/month)
- Google Gemini Flash-Lite on Oracle Cloud free tier

### Budget Tier ($3-8/month)
- Claude 3.5 Haiku (~$3/month for moderate use)
- GPT-4.1-mini (~$8/month)
- DeepSeek V3.2: ~$0.53 per million tokens

### Best Value (Recommended "Sweet Spot")
Use a multi-model routing strategy:

| Role | Model | Cost |
|------|-------|------|
| Routine tasks | Gemini Flash-Lite | ~$0.50/M tokens |
| Main workhorse | Claude Sonnet 4 or Gemini 2.5 Flash | moderate |
| Complex tasks | Claude Opus or GPT-5.x | only when needed |

**Recommended setup:** Use OpenRouter as your provider -- it gives access to all models through one API key and has an Auto Model feature that picks the cheapest model per prompt. Estimated cost: $3-10/month for moderate personal use.

### Cost Warning
One user documented spending $500 unexpectedly by leaving OpenClaw running with an expensive model. Cheaper models may fail complex tasks, triggering retries on more expensive models. Always set spending limits on your API provider accounts.

---

## Safety Considerations

### Critical Vulnerability (Patched)
A high-severity flaw (CVE-2026-25253, CVSS 8.8) allowed one-click remote code execution via a malicious link. The Control UI trusted `gatewayUrl` from query strings without validation. Patched in version 2026.1.29 (January 30, 2026). Always run the latest version.

### Fundamental Security Risks
1. Shell access: OpenClaw can run shell commands, read/write files. A misconfigured or malicious skill can cause serious damage.
2. Credential exposure: OpenClaw has been reported to leak plaintext API keys via prompt injection or unsecured endpoints.
3. Malicious skills (supply chain risk): The skills registry is essentially a supply chain. Like installing an unvetted npm package with root access.
4. Prompt injection: Adversaries can embed malicious instructions in data sources (emails, web pages).
5. Network exposure: If the gateway is exposed to the internet without proper authentication, attackers can connect directly.

### Safety Best Practices
- Always update to the latest version: `npm update -g openclaw@latest`
- Never expose OpenClaw to the public internet. Run behind a VPN (Tailscale recommended).
- Use gateway tokens and/or OAuth for access controls
- Vet all skills before installing -- do not blindly install community skills
- Set API spending limits on all provider accounts
- Do not run on corporate/work machines without security team approval
- Use Docker isolation if possible
- Review permissions carefully during onboarding

---

## Sources

- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
- [OpenClaw Official Documentation](https://docs.openclaw.ai/install)
- [OpenClaw Model Providers Documentation](https://docs.openclaw.ai/concepts/model-providers)
- [DigitalOcean - What is OpenClaw?](https://www.digitalocean.com/resources/articles/what-is-openclaw)
- [OpenClaw Deploy Cost Guide](https://yu-wenhao.com/en/blog/2026-02-01-openclaw-deploy-cost-guide)
- [Best Models for OpenClaw in 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot)
- [CrowdStrike Security Analysis](https://www.crowdstrike.com/en-us/blog/what-security-teams-need-to-know-about-openclaw-ai-super-agent/)
- [JFrog Security Analysis](https://jfrog.com/blog/giving-openclaw-the-keys-to-your-kingdom-read-this-first/)
- [Cisco Security Concerns](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare)
- [1Password - Skills Attack Surface](https://1password.com/blog/from-magic-to-malware-how-openclaws-agent-skills-become-an-attack-surface)
- [The Hacker News - CVE-2026-25253](https://thehackernews.com/2026/02/openclaw-bug-enables-one-click-remote.html)
- [OpenRouter - OpenClaw Integration](https://openrouter.ai/docs/guides/guides/openclaw-integration)

---

*Generated by Assistant Brain OS - February 2026*
