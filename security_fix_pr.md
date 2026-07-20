### Security Fixes
This Pull Request addresses the final two security vulnerabilities flagged by the Greptile Security Review on the Cloudflare Tunnel integration.

1. **Unverified Binary Download Execution**: 
   The `cloudflared` binary download now pins an exact version release (`2026.7.2`) and strictly verifies the `SHA256` checksum (`ec905ea7b7e327ff8abdde8cb64697a2152de74dbcdbf6aec9db8364eb3886cd`) before applying executable permissions. If a tampered binary or redirect is intercepted, the installation halts immediately, preventing rogue code from executing as a systemd service.
   
2. **Ciphertext Passthrough Leak**: 
   The `decrypt()` utility function no longer falls back to returning the raw ciphertext string if it fails to detect the colon (`:`) delimiter. It now strictly raises a `ValueError("Invalid ciphertext format: missing delimiter")`. This prevents manually tampered or broken configurations from leaking encrypted tokens over the network to the Cloudflare API during runtime checks.
