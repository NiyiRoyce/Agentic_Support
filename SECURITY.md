# Security Policy

## Secrets Management

### Environment Variables
All sensitive configuration must be provided via environment variables, never committed to the repository.

1. **Development Setup:**
   - Copy `.env.example` to `.env` locally
   - Update `.env` with your development credentials
   - `.env` is gitignored and will not be committed

2. **Production Deployment:**
   - Secrets are injected via container orchestration (Kubernetes secrets, Docker secrets, CI/CD secrets)
   - NEVER commit production credentials to any branch
   - Use a secrets management service (HashiCorp Vault, AWS Secrets Manager, etc.)

### Required Secrets
- `OPENAI_API_KEY`: OpenAI API key for LLM provider
- `DATABASE_URL`: PostgreSQL connection string (if using database persistence)
- `RAG_VECTOR_STORE_PATH`: Path to vector store (local development only; use service in production)

### Credential Rotation
If credentials are ever accidentally committed:
1. Immediately notify the security team
2. Rotate all compromised credentials
3. File a security incident report
4. Review git history for other potential leaks

### Pre-commit Hooks
This repository is protected by secret-scanning pre-commit hooks. These will reject commits containing:
- API keys (AWS, OpenAI, Anthropic, etc.)
- Database credentials
- Private key files
- Other sensitive patterns

### CI/CD Security
- GitHub Actions use encrypted secrets stored in repository settings
- Secrets are never logged or exposed in build output
- All dependencies are regularly scanned for known vulnerabilities

### Reporting Security Issues
If you discover a security vulnerability, please email niyiroyce@gmail.com with:
- Description of the issue
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

## References
- [OWASP Secrets Management](https://owasp.org/www-community/Sensitive_Data_Exposure)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
