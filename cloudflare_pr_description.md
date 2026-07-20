### Summary
This PR implements native **Cloudflare Tunnel (cloudflared)** integration directly within the Pilot admin UI. It solves the critical problem of exposing local development and staging environments to the public internet securely, **without requiring a public IP address, port forwarding, or complex firewall configurations**.

By embedding this integration, developers can expose any bench site to a public domain in a single click, instantly sharing their work with clients or external webhooks.

### Key Features
1. **Zero-Config Public Access**: Completely bypasses the need for public IPs or NAT traversal by establishing an outbound-only connection to Cloudflare's edge network.
2. **Dual Authentication Methods**:
    * **Method 1: API Token Integration**: Fully programmatic integration using Cloudflare API tokens. Automatically configures ingress rules, creates CNAME DNS records, and manages the tunnel lifecycle directly from the UI.
    * **Method 2: Cloudflared SSO (Interactive Login)**: For users who don't want to generate API tokens, this implements an OAuth-like flow that opens the Cloudflare interactive login directly. It captures the resulting `cert.pem` and configures a local `config.yml` to route traffic.
3. **Automatic DNS Routing**: Automatically points custom domains to the tunnel UUID via `cloudflared tunnel route dns` (for SSO) or Cloudflare REST API (for API Tokens).
4. **Local Subprocess Management**: Robustly starts, stops, and monitors the `cloudflared` daemon as a background service using Python's `subprocess` and threading, ensuring the tunnel stays alive alongside the bench.

### Technical Details & Security Measures
* **Credential Protection**: API tokens and Tunnel secrets are encrypted symmetrically before being stored in `bench.toml` using `pilot.utils.encrypt/decrypt`. This prevents plain-text credential leakage.
* **Greptile Review Pre-Checks**:
  * Eliminated hardcoded executable paths (`cloudflared_path = shutil.which("cloudflared")`) to ensure cross-platform compatibility.
  * Ensured `cloudflared` subprocess invocations do not leak sensitive credentials via command-line arguments (using configuration files and encrypted token extraction instead).
  * Removed unused and redundant standard library imports to maintain strict linting compliance.
* **Process Lifecycle**: The `cloudflared` daemon is gracefully stopped and started when settings are toggled. A fallback `_cancel_login_process` prevents zombie interactive login threads if a user abandons the SSO flow mid-way.

### Verification
* Tested exposing a local site via both API Token (creates CNAME and Ingress automatically) and SSO (local `config.yml`).
* Verified `bench.toml` properly reflects the active Cloudflare integration state without leaking raw secrets.
* Confirmed the UI correctly reads the tunnel status and exposes the correct internal port.
