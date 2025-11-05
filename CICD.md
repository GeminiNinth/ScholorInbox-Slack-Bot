# CI/CD Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) workflows for the Scholar Inbox Slack Bot project.

## Overview

The project uses GitHub Actions for automated testing, linting, security scanning, and releases. The workflows are designed to ensure code quality and facilitate smooth deployments.

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### Test Job
- **Purpose**: Run unit tests across multiple Python versions
- **Python Versions**: 3.11, 3.12
- **Steps**:
  1. Checkout code
  2. Set up Python
  3. Install `uv` package manager
  4. Install project dependencies
  5. Install Playwright browsers
  6. Run pytest with coverage
  7. Upload coverage to Codecov

**Environment Variables** (for testing):
```yaml
SCHOLAR_INBOX_SECRET_URL: "https://scholar-inbox.com/login/test"
SLACK_BOT_TOKEN: "xoxb-test-token"
SLACK_CHANNEL_ID: "C0123456789"
OPENAI_API_KEY: "sk-test-key"
```

#### Lint Job
- **Purpose**: Check code quality and formatting
- **Tools**:
  - `ruff`: Fast Python linter and formatter
  - `mypy`: Static type checker
- **Steps**:
  1. Run ruff linter
  2. Check code formatting with ruff
  3. Run mypy type checking

#### Security Job
- **Purpose**: Scan for security vulnerabilities
- **Tools**:
  - `safety`: Check for known security vulnerabilities in dependencies
  - `bandit`: Find common security issues in Python code
- **Steps**:
  1. Run safety check on dependencies
  2. Run bandit security scan on source code

### 2. Release Workflow (`.github/workflows/release.yml`)

**Triggers:**
- Push of version tags (e.g., `v1.0.0`, `v1.2.3`)

**Jobs:**

#### Create Release Job
- **Purpose**: Create GitHub release with artifacts
- **Steps**:
  1. Checkout code
  2. Set up Python and install dependencies
  3. Run tests to ensure quality
  4. Extract version from tag
  5. Create source code archive
  6. Generate changelog
  7. Create GitHub release with:
     - Release notes
     - Source code archive
     - Installation instructions

#### Docker Build Job
- **Purpose**: Build and push Docker image to GitHub Container Registry
- **Steps**:
  1. Checkout code
  2. Set up Docker Buildx
  3. Log in to GitHub Container Registry (ghcr.io)
  4. Extract metadata for tags
  5. Build and push Docker image with tags:
     - `latest`
     - `v1.2.3` (semantic version)
     - `v1.2` (major.minor)
     - `v1` (major)

## Docker Support

### Dockerfile

The project includes a `Dockerfile` for containerized deployment:

```dockerfile
FROM python:3.11-slim
# Installs uv, dependencies, and Playwright
# Runs bot in scheduled mode
```

### Building Docker Image Locally

```bash
# Build image
docker build -t scholar-inbox-slack-bot .

# Run container
docker run -d \
  --name scholar-inbox-bot \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/data:/app/data \
  scholar-inbox-slack-bot
```

### Using Pre-built Image from GitHub Container Registry

```bash
# Pull image
docker pull ghcr.io/YOUR_USERNAME/scholar-inbox-slack-bot:latest

# Run container
docker run -d \
  --name scholar-inbox-bot \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/data:/app/data \
  ghcr.io/YOUR_USERNAME/scholar-inbox-slack-bot:latest
```

## Setting Up CI/CD

### Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **Branch Protection**: (Optional) Set up branch protection rules for `main`

### Required Secrets

No additional secrets are required for basic CI/CD. The workflows use:
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- Test environment variables: Hard-coded in workflow files

### Optional: Codecov Integration

To enable code coverage reporting:

1. Sign up at [codecov.io](https://codecov.io)
2. Add your repository
3. No additional secrets needed (uses `GITHUB_TOKEN`)

## Creating a Release

### Manual Release

1. **Update version** in relevant files (if applicable)
2. **Create and push a tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. **Workflow automatically**:
   - Runs tests
   - Creates GitHub release
   - Builds and pushes Docker image

### Tag Format

Use semantic versioning: `vMAJOR.MINOR.PATCH`

Examples:
- `v1.0.0` - Initial release
- `v1.1.0` - New features
- `v1.1.1` - Bug fixes

## Monitoring Workflows

### Viewing Workflow Runs

1. Go to your GitHub repository
2. Click on "Actions" tab
3. View workflow runs and logs

### Workflow Status Badges

Add to your README:

```markdown
![CI](https://github.com/YOUR_USERNAME/scholar-inbox-slack-bot/workflows/CI/badge.svg)
![Release](https://github.com/YOUR_USERNAME/scholar-inbox-slack-bot/workflows/Release/badge.svg)
```

## Troubleshooting

### Tests Failing in CI

1. **Check logs** in GitHub Actions
2. **Run tests locally**:
   ```bash
   uv run pytest tests/ -v
   ```
3. **Verify environment variables** are set correctly

### Docker Build Failing

1. **Check Dockerfile** syntax
2. **Test build locally**:
   ```bash
   docker build -t test .
   ```
3. **Verify dependencies** in `requirements.txt`

### Release Not Creating

1. **Verify tag format**: Must match `v*.*.*`
2. **Check permissions**: Repository must allow workflow to create releases
3. **Review workflow logs** for errors

## Best Practices

1. **Always run tests locally** before pushing
2. **Use feature branches** and pull requests
3. **Review CI results** before merging
4. **Keep dependencies updated** regularly
5. **Monitor security scans** and address vulnerabilities
6. **Test Docker image** before releasing

## Customization

### Modifying CI Workflow

Edit `.github/workflows/ci.yml`:

```yaml
# Add more Python versions
strategy:
  matrix:
    python-version: ['3.11', '3.12', '3.13']

# Add more test commands
- name: Run integration tests
  run: pytest tests/test_integration.py -v
```

### Customizing Release Notes

Edit `.github/workflows/release.yml`:

```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    body: |
      # Custom release notes
      Your custom content here
```

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Semantic Versioning](https://semver.org/)
- [Codecov Documentation](https://docs.codecov.com/)

## Support

For issues with CI/CD:
1. Check workflow logs
2. Review this documentation
3. Open an issue on GitHub
