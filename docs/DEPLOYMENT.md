# LinuxONE operations

Run `infra/install_linuxone.sh` as root from the extracted bundle on Ubuntu s390x. It installs the required Python/venv tools, OS CBC and optional pinned PuLP. The core and learned model need no third-party libraries. No existing notebook project is overwritten.

Ports: coordinator8000; Factory A8001; Factory B8002; supplier8003. All bind127.0.0.1. Evaluator is a separate filesystem worker. Inbound access is through SSH22 and a local tunnel, so no firewall opening is needed. Existing services on unrelated ports are not stopped.

Paths:

- `/opt/tradeoff`: source, included learned model, virtual environment; root-owned.
- `/var/lib/tradeoff/factory_a`, factory_b, supplier_s: private stores and owner-only service credentials.
- `/var/lib/tradeoff/coordinator`: audit DB, coordinator configuration and dashboard token.
- `/var/lib/tradeoff/evaluator`: privileged evaluator configuration.
- `/var/lib/tradeoff/exchange`: coordinator writes, evaluator reads.
- `/var/lib/tradeoff/reports`: evaluator writes, coordinator reads.
- `/etc/tradeoff/llm.env`: coordinator-only configuration (local ML is the default).

The generic systemd unit runs each role with a distinct user. Unix directory/file permissions enforce isolation; `ProtectSystem`, `ProtectHome` and `NoNewPrivileges` further restrict services. The evaluator deliberately has read access to synthetic private databases. Root remains trusted.

```bash
sudo systemctl status tradeoff@coordinator
sudo journalctl -u tradeoff@coordinator -n 50 --no-pager
sudo systemctl restart tradeoff@coordinator
sudo bash /opt/tradeoff/infra/verify_isolation.sh
```

Edit model/provider settings with `sudoedit /etc/tradeoff/llm.env`. Only the coordinator reads that file. The shipped artifact supports local AI without credentials. External model inference is optional and is not represented as running on LinuxONE when hosted elsewhere.

When forwarding, `ssh -L 8080:127.0.0.1:8000 ...` permits opening127.0.0.1:8080 locally even when8000 is occupied by a local dev instance. Host validation allows loopback hosts with the forwarded local port and requires Origin to match. Do not use external hostnames or proxy the basic demo onto a public domain without a production serving/authentication layer.

For a clean demo, use the reset-view endpoint. It preserves audit/run history. Do not delete participant DBs or regenerate credentials during a live event. Installer reruns preserve existing initialized state and provider configuration. Back up `/var/lib/tradeoff` through a trusted administrative channel if needed; it contains credentials/private data and must never enter the public source ZIP.

Package source with `python -m tradeoff package`; `MANIFEST.json` lists per-file SHA-256. Verify the source bundle checksum before installing on the VM. The Windows deployment helper retains ordinary SSH host-key verification. Never disable host-key verification to work around an unknown fingerprint.
