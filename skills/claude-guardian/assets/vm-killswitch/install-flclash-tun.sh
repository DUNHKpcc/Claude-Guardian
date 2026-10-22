#!/usr/bin/env bash
# 脱敏版（2026-10-21）：由所有者的脚本整理，逻辑不变，只把版本和架构改成可覆盖的参数。
# 在 Arch 系 Linux 客机（如 Omarchy）里由用户自己运行；用 pacman 装依赖，以 root 装 FlClash 和 TUN 助手。
# 先打快照、先读一遍脚本；运行会下载 FlClash 的 GitHub Release 并核对 SHA256，校验失败即中止。
# 版本固定为脚本编写时的 0.9.1，升级前到 FlClash 的 Release 页面核对；架构默认 arm64（Apple 芯片 Mac 上的客机），
# x86_64 客机请按 Release 页面的实际文件名设置 ARCH。装完后打开 FlClash 导入自己的节点配置并开启 TUN，再装 killswitch。
set -euo pipefail

version="${FLCLASH_VERSION:-0.9.1}"
arch="${ARCH:-arm64}"
base="https://github.com/chen08209/FlClash/releases/download/v${version}"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading and verifying FlClash ${arch}..."
curl -L --silent --show-error --fail --max-time 90 \
  -o "$tmp/FlClash.deb" \
  "$base/FlClash-${version}-linux-${arch}.deb"
curl -L --silent --show-error --fail --max-time 30 \
  -o "$tmp/SHA256SUMS" \
  "$base/SHA256SUMS"
expected=$(awk -v name="./FlClash-${version}-linux-${arch}.deb" '$2==name{print $1}' "$tmp/SHA256SUMS")
actual=$(sha256sum "$tmp/FlClash.deb" | awk '{print $1}')
[[ -n "$expected" && "$expected" == "$actual" ]] || {
  echo 'Checksum verification failed; aborting.' >&2
  exit 1
}

echo 'Installing runtime libraries (sudo password required)...'
sudo pacman -S --needed libayatana-indicator ayatana-ido

mkdir "$tmp/ar"
ar x "$tmp/FlClash.deb" --output "$tmp/ar"
echo 'Installing root-owned FlClash files under /opt/FlClash...'
sudo zstd -dc "$tmp/ar/data.tar.zst" | sudo tar -xpf - -C /
sudo chown -R root:root /opt/FlClash
sudo chmod 0755 /opt/FlClash /opt/FlClash/FlClash /opt/FlClash/FlClashCore /opt/FlClash/FlClashHelperService

cat > "$tmp/flclash.desktop" <<'EOF'
[Desktop Entry]
Name=FlClash
Comment=Clash Meta proxy client
Exec=/opt/FlClash/FlClash
Icon=/opt/FlClash/data/flutter_assets/assets/images/icon.png
Terminal=false
Type=Application
Categories=Network;
StartupNotify=true
StartupWMClass=com.follow.clash
EOF
sudo install -Dm644 "$tmp/flclash.desktop" /usr/share/applications/flclash.desktop

mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/flclash.desktop" <<'EOF'
[Desktop Entry]
Name=FlClash
Comment=Start FlClash at login
Exec=/opt/FlClash/FlClash
Icon=/opt/FlClash/data/flutter_assets/assets/images/icon.png
Terminal=false
Type=Application
X-GNOME-Autostart-enabled=true
EOF

# v0.9.1 accepts only: install (not install --owner-pid ...).
echo 'Installing the privileged TUN helper...'
sudo /opt/FlClash/FlClashHelperService install

systemctl is-active --quiet flclash-helper.service
systemctl is-enabled --quiet flclash-helper.service
printf '\nTUN helper installed and enabled: '
systemctl is-active flclash-helper.service
printf 'FlClash executable: /opt/FlClash/FlClash\n'
printf 'Now open FlClash and enable TUN.\n'
