# 🔒 Security Checklist - Assistant Brain OS

## ✅ Security Measures Implemented

This document tracks security best practices and measures.

---

## 🛡️ Critical Security Checks

### ✅ Environment Variables
- [x] `.env` file in `.gitignore`
- [x] `.env.example` provided for reference
- [x] No hardcoded API keys in code
- [x] Environment variables loaded via `python-dotenv`

### ✅ Git Protection
- [x] Comprehensive `.gitignore` created
- [x] Sensitive files excluded from version control
- [x] Database files excluded
- [x] Log files excluded
- [x] User data directories excluded

### ✅ API Key Management
- [x] Keys stored in environment variables only
- [x] Separate keys for different services
- [x] Keys never logged or printed
- [ ] Key rotation schedule (recommended: quarterly)
- [ ] Key permissions limited to necessary scopes

### ✅ Data Protection
- [x] User data stored locally (not in cloud)
- [x] Database files excluded from git
- [x] Vector store data excluded from git
- [x] Backup files excluded from git

### ✅ Code Security
- [x] No secrets in source code
- [x] No credentials in comments
- [x] Configuration separated from code
- [x] Test files don't contain real credentials

---

## 🔍 Files That Should NEVER Be Committed

### Critical Files (Already Protected)
```
❌ .env                          # Contains all secrets
❌ .env.local, .env.*            # Any environment files
❌ *key*.json                    # Key files
❌ *secret*.json                 # Secret files
❌ *credentials*.json            # Credential files
❌ *.pem, *.key, *.cert         # Certificates
❌ data/*.db                     # Database files
❌ data/chroma/                  # Vector database
❌ qdrant_data/                  # Qdrant data
❌ logs/*.log                    # Log files
❌ .pm2/                         # PM2 logs
❌ temp/*.ogg, *.mp3            # Voice recordings
❌ dump.rdb                      # Redis dumps
```

### Personal Files
```
❌ notes.md                      # Personal notes
❌ todo.md                       # Todo lists
❌ PERSONAL_*.md                 # Personal docs
```

---

## 📋 Security Audit Checklist

### Before First Commit
- [ ] Review all files being committed
- [ ] Ensure no `.env` file is included
- [ ] Check for API keys in code
- [ ] Verify `.gitignore` is working
- [ ] Remove any test data with real info

### Regular Audits (Weekly/Monthly)
- [ ] Check git status for sensitive files
- [ ] Review recent commits for leaks
- [ ] Audit API key usage and permissions
- [ ] Check logs for exposed credentials
- [ ] Verify backup security

### Before Deployment
- [ ] All secrets in environment variables
- [ ] Production keys different from dev
- [ ] Database backed up securely
- [ ] Logs don't contain sensitive data
- [ ] Error messages don't expose secrets

---

## 🚨 What to Do If Secrets Are Exposed

### Immediate Actions (Within 1 Hour)

1. **Rotate All Compromised Keys**
   ```bash
   # Immediately regenerate:
   - OpenAI API key
   - DeepSeek API key
   - Telegram bot token
   ```

2. **Revoke Old Keys**
   - Revoke exposed keys in respective platforms
   - Update `.env` with new keys
   - Restart all services

3. **Remove from Git History** (if committed)
   ```bash
   # WARNING: This rewrites history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (coordinate with team first!)
   git push origin --force --all
   ```

4. **Notify Affected Parties**
   - Inform team members
   - Monitor for unauthorized usage
   - Review access logs

### Prevention Going Forward
- [ ] Enable pre-commit hooks
- [ ] Use git-secrets tool
- [ ] Regular security training
- [ ] Automated secret scanning

---

## 🔐 Best Practices

### API Key Management

**DO:**
- ✅ Store in environment variables
- ✅ Use different keys for dev/prod
- ✅ Rotate keys regularly
- ✅ Limit key permissions
- ✅ Monitor usage patterns
- ✅ Set spending limits

**DON'T:**
- ❌ Hardcode in source code
- ❌ Commit to version control
- ❌ Share via chat/email
- ❌ Use in client-side code
- ❌ Log keys in output
- ❌ Store in databases

### Environment Files

**Correct Setup:**
```bash
# .env (ignored by git)
OPENAI_API_KEY=sk-real-key-here
DEEPSEEK_API_KEY=sk-real-key-here

# .env.example (committed to git)
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
```

### Database Security

**Protect:**
- User knowledge data
- Chat history
- Vector embeddings
- Job history
- User settings

**How:**
- Exclude from git
- Regular backups
- Encrypt sensitive fields (if needed)
- Access controls
- Audit trails

---

## 🛠️ Security Tools

### Git Secrets Prevention

**Install git-secrets:**
```bash
# macOS
brew install git-secrets

# Ubuntu/Debian
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets && make install

# Configure for repository
cd /root/assistant-brain-os
git secrets --install
git secrets --register-aws
```

**Add custom patterns:**
```bash
git secrets --add 'OPENAI_API_KEY.*'
git secrets --add 'DEEPSEEK_API_KEY.*'
git secrets --add 'TELEGRAM_TOKEN.*'
git secrets --add 'sk-[a-zA-Z0-9]{32,}'
```

### Pre-commit Hook

**Create `.git/hooks/pre-commit`:**
```bash
#!/bin/bash

echo "🔍 Checking for sensitive files..."

# Check for .env file
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ ERROR: Attempting to commit .env file!"
    echo "   This file contains sensitive information."
    exit 1
fi

# Check for potential secrets in code
if git diff --cached | grep -iE "(api_key|secret|password|token).*=.*['\"][^'\"]{20,}"; then
    echo "⚠️  WARNING: Potential secret detected in code!"
    echo "   Please review your changes carefully."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Security checks passed"
exit 0
```

**Make executable:**
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📊 Sensitive Data Inventory

### API Keys & Tokens
| Service | Location | Rotation Frequency |
|---------|----------|-------------------|
| OpenAI | `.env` | Quarterly |
| DeepSeek | `.env` | Quarterly |
| Telegram | `.env` | When compromised |

### Databases
| Database | Contains | Backup Location |
|----------|----------|----------------|
| SQLite | User data, metadata | Local encrypted |
| ChromaDB | Vector embeddings | Local encrypted |
| Redis | Job queue (temporary) | Not backed up |

### User Data
| Type | Storage | Retention |
|------|---------|-----------|
| Knowledge entries | SQLite + ChromaDB | Indefinite |
| Voice recordings | Temp files (deleted) | Immediate |
| Chat history | Job history | 30 days |
| User settings | Redis | Indefinite |

---

## 🔄 Key Rotation Schedule

### Quarterly (Every 3 Months)
- [ ] Rotate OpenAI API key
- [ ] Rotate DeepSeek API key
- [ ] Update production `.env`
- [ ] Update development `.env`
- [ ] Test all integrations

### Annually
- [ ] Audit all access permissions
- [ ] Review security practices
- [ ] Update security documentation
- [ ] Team security training

### Immediately (If Compromised)
- [ ] Revoke compromised keys
- [ ] Generate new keys
- [ ] Update all environments
- [ ] Review access logs
- [ ] Notify stakeholders

---

## 📝 Security Incident Log

### Template for Incidents

```markdown
## Incident: [Date]

**Type:** API key exposure / Data leak / etc.
**Severity:** Critical / High / Medium / Low
**Discovery:** How was it found?
**Impact:** What was affected?
**Response:** What actions were taken?
**Prevention:** How to prevent in future?
**Status:** Resolved / In Progress / Monitoring
```

### Example Entry

```markdown
## Incident: 2026-02-03

**Type:** None - Initial setup
**Severity:** N/A
**Discovery:** Preventive setup
**Impact:** None
**Response:** Created comprehensive .gitignore and security measures
**Prevention:** Established security checklist and best practices
**Status:** Preventive measures in place
```

---

## ✅ Quick Security Commands

```bash
# Check what's being tracked by git
git ls-files

# Check for .env in git
git ls-files | grep ".env"

# Remove .env from git if accidentally added
git rm --cached .env
git commit -m "Remove .env from tracking"

# Scan for potential secrets in staged files
git diff --cached | grep -iE "(api_key|secret|password|token)"

# View what will be committed
git status
git diff --cached

# Test .gitignore rules
git check-ignore -v .env
git check-ignore -v data/brain.db
```

---

## 🎯 Security Score

Rate your security posture:

- [x] Secrets not in code (10 points)
- [x] .gitignore comprehensive (10 points)
- [x] .env.example provided (5 points)
- [x] Database excluded from git (10 points)
- [x] Logs excluded from git (5 points)
- [ ] Pre-commit hooks active (10 points)
- [ ] Git-secrets installed (10 points)
- [ ] Keys rotated regularly (10 points)
- [ ] Monitoring in place (10 points)
- [ ] Security training done (5 points)

**Current Score: 40/85**
**Target Score: 75/85 (Good)**

---

## 📚 Additional Resources

- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [Git Secrets](https://github.com/awslabs/git-secrets)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [OpenAI API Key Safety](https://platform.openai.com/docs/guides/safety-best-practices)

---

**🔒 Security is everyone's responsibility. Stay vigilant!**

**Last Updated:** 2026-02-03
**Next Review:** 2026-05-03
