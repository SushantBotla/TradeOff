#!/usr/bin/env bash
# Run as root on the intended LinuxONE Ubuntu VM, from an extracted source bundle.
set -euo pipefail
umask 027
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
app_dir=/opt/tradeoff
state_dir=/var/lib/tradeoff
if [[ ${EUID} -ne 0 ]]; then echo "Run: sudo bash infra/install_linuxone.sh" >&2; exit 1; fi
if [[ "$(uname -m)" != s390x ]]; then
  echo "This installer targets an s390x LinuxONE VM. For local development use python -m tradeoff dev." >&2
  exit 1
fi
apt-get update
apt-get install -y python3 python3-venv coinor-cbc openssh-client
install -d -m 0755 "$app_dir"
for entry in tradeoff infra docs models tests README.md LICENSE pyproject.toml requirements-solver.txt .env.example; do
  cp -a -- "$source_dir/$entry" "$app_dir/"
done
chown -R root:root "$app_dir"
find "$app_dir/tradeoff" "$app_dir/infra" "$app_dir/docs" "$app_dir/models" "$app_dir/tests" -type d -exec chmod 0755 {} +
find "$app_dir/tradeoff" "$app_dir/infra" "$app_dir/docs" "$app_dir/models" "$app_dir/tests" -type f -exec chmod 0644 {} +
python3 -m venv "$app_dir/venv"
if ! "$app_dir/venv/bin/python" -m pip install -r "$app_dir/requirements-solver.txt"; then
  echo "Optional PuLP installation failed. The exact standard-library solver remains available." >&2
fi
# The installer uses a restrictive umask; service identities still need to
# traverse/read the root-owned, credential-free runtime and its packages.
chmod -R a+rX "$app_dir/venv"
for group in tradeoff-evaluator tradeoff-exchange tradeoff-reports; do
  getent group "$group" >/dev/null || groupadd --system "$group"
done
for role in factory_a factory_b supplier_s coordinator evaluator; do
  user="tradeoff-$role"
  if ! id "$user" >/dev/null 2>&1; then
    if getent group "$user" >/dev/null; then
      useradd --system --gid "$user" --no-create-home --shell /usr/sbin/nologin "$user"
    else
      useradd --system --user-group --no-create-home --shell /usr/sbin/nologin "$user"
    fi
  fi
done
install -d -m 0711 "$state_dir"
cd "$app_dir"
"$app_dir/venv/bin/python" -m tradeoff init --root "$state_dir" --isolated
chmod 0711 "$state_dir"
for role in factory_a factory_b supplier_s; do
  chown -R "tradeoff-$role:tradeoff-evaluator" "$state_dir/$role"
  chmod 0750 "$state_dir/$role"
  chmod 0640 "$state_dir/$role/private.db"
  chmod 0600 "$state_dir/$role/config.json"
done
chown -R tradeoff-coordinator:tradeoff-coordinator "$state_dir/coordinator"
chown -R tradeoff-evaluator:tradeoff-evaluator "$state_dir/evaluator"
chmod 0700 "$state_dir/coordinator" "$state_dir/evaluator"
chown tradeoff-coordinator:tradeoff-exchange "$state_dir/exchange"
chmod 2750 "$state_dir/exchange"
chown tradeoff-evaluator:tradeoff-reports "$state_dir/reports"
chmod 2750 "$state_dir/reports"
usermod -a -G tradeoff-exchange tradeoff-evaluator
usermod -a -G tradeoff-reports tradeoff-coordinator
install -d -m 0750 -o root -g tradeoff-coordinator /etc/tradeoff
if [[ ! -e /etc/tradeoff/llm.env ]]; then
  install -m 0640 -o root -g tradeoff-coordinator "$app_dir/.env.example" /etc/tradeoff/llm.env
fi
install -m 0644 "$app_dir/infra/tradeoff@.service" /etc/systemd/system/tradeoff@.service
install -d -m 0755 /etc/systemd/system/tradeoff@coordinator.service.d
cat > /etc/systemd/system/tradeoff@coordinator.service.d/dependencies.conf <<'EOF'
[Unit]
Requires=tradeoff@factory_a.service tradeoff@factory_b.service tradeoff@supplier_s.service tradeoff@evaluator.service
After=tradeoff@factory_a.service tradeoff@factory_b.service tradeoff@supplier_s.service tradeoff@evaluator.service
EOF
systemctl daemon-reload
for role in factory_a factory_b supplier_s evaluator coordinator; do
  systemctl enable "tradeoff@$role.service"
  systemctl restart "tradeoff@$role.service"
done
bash "$app_dir/infra/verify_isolation.sh"
ready=0
for attempt in {1..30}; do
  if runuser -u tradeoff-coordinator -- "$app_dir/venv/bin/python" -m tradeoff doctor --config "$state_dir/coordinator/config.json" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ $ready -ne 1 ]]; then
  echo "Service readiness failed; inspect journalctl -u tradeoff@coordinator." >&2
  exit 1
fi
echo "Installed with local ML enabled. Optional LLM settings: sudoedit /etc/tradeoff/llm.env, then restart tradeoff@coordinator."
echo "SSH tunnel from laptop: ssh -L 8000:127.0.0.1:8000 USER@VM"
echo "Print dashboard token: sudo -u tradeoff-coordinator $app_dir/venv/bin/python -m tradeoff token --config $state_dir/coordinator/config.json"

