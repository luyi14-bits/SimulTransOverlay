# Security Policy

## Supported Versions
Latest release only.

## Reporting a Vulnerability
Open a GitHub Issue with the label `security` or email the maintainers directly.
Do NOT disclose security vulnerabilities publicly until they have been addressed.

## Security Design
- All audio processing is local — no data leaves your machine
- API keys should use environment variables, not hardcoded config
- Models are downloaded over HTTPS from trusted sources (HuggingFace / ModelScope)
- The app only connects to localhost (Ollama) unless DeepSeek API is explicitly configured
