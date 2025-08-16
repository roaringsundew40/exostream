#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ---------- colors ----------
ORANGE=$'\033[38;5;208m'; RESET=$'\033[0m'
info(){ printf '%b\n' "${ORANGE}INFO:${RESET} $*"; }
die(){  printf '%b\n' "${ORANGE}ERROR:${RESET} $*" >&2; exit 1; }

# ---------- config (renamed to exostream) ----------
EXO_USER="exostream-user"
EXO_GROUP="exostream-admins"
EXO_HOME="/home/${EXO_USER}"
FFMPEG_NDI_DIR="${EXO_HOME}/FFMPEG-NDI"
FFMPEG_SRC_DIR="${EXO_HOME}/ffmpeg"
INST_DIR="${EXO_HOME}/instances"
LOG_DIR="${EXO_HOME}/logs"
CLI_REAL="/usr/local/bin/exostream.real"
CLI_WRAPPER="/usr/local/bin/exostream"
SUDOERS_FILE="/etc/sudoers.d/exostream"
GET_THROTTLE_URL="https://raw.githubusercontent.com/alwye/get_throttled/refs/heads/master/get_throttled.sh"
GET_THROTTLE_DEST="${EXO_HOME}/get_throttle.sh"
PKGS=(sudo git curl wget build-essential pkg-config tmux yasm nasm libv4l-dev ca-certificates)

[[ $EUID -eq 0 ]] || die "Run as root (sudo)."
INVOKER="${SUDO_USER:-$(id -un)}"

# ---------- prompts ----------
echo
info "Pre-install questions (answer now; build runs unattended):"
read -rp $'Which Raspberry Pi model? [4 or 3] (default 4): ' PI_MODEL; PI_MODEL="${PI_MODEL:-4}"
[[ "$PI_MODEL" == "4" || "$PI_MODEL" == "3" ]] || die "Pi model must be 3 or 4."
ARCH="$(dpkg --print-architecture 2>/dev/null || echo unknown)"
info "Detected Debian architecture: ${ARCH}"
read -rp $'Proceed to build FFmpeg now? [Y/n]: ' BUILD; BUILD="${BUILD:-Y}"

# ---------- system prep ----------
info "Installing base packages: ${PKGS[*]}"
apt update
DEBIAN_FRONTEND=noninteractive apt install -y "${PKGS[@]}"

# absolute paths for sudoers
TMUX_PATH="$(command -v tmux || true)"; [[ "$TMUX_PATH" == /* ]] || TMUX_PATH="/usr/bin/tmux"
if [[ -x /bin/kill ]]; then KILL_PATH="/bin/kill"
elif [[ -x /usr/bin/kill ]]; then KILL_PATH="/usr/bin/kill"
else die "Could not find absolute path to 'kill' binary"; fi

# user/group
if ! getent group "${EXO_GROUP}" >/dev/null; then
  info "Creating group ${EXO_GROUP}"; groupadd -r "${EXO_GROUP}"
else info "Group ${EXO_GROUP} already exists"; fi

if ! id -u "${EXO_USER}" >/dev/null 2>&1; then
  info "Creating system user ${EXO_USER} (${EXO_HOME})"
  useradd --system --create-home --shell /bin/bash --home-dir "${EXO_HOME}" "${EXO_USER}"
else info "User ${EXO_USER} already exists"; fi

info "Adding ${INVOKER} and root to ${EXO_GROUP}"
usermod -aG "${EXO_GROUP}" "${INVOKER}" || true
usermod -aG "${EXO_GROUP}" root || true

# ---- give runtime user device access (fixes /dev/video* permission) ----
for g in video audio render; do
  if getent group "$g" >/dev/null; then usermod -aG "$g" "${EXO_USER}" || true; fi
done
# ensure no old tmux server is holding stale groups; safe even if none running
sudo -u "${EXO_USER}" tmux kill-server >/dev/null 2>&1 || true

# dirs
info "Preparing directories"
mkdir -p "${EXO_HOME}" "${INST_DIR}" "${LOG_DIR}"
chown -R "${EXO_USER}:${EXO_USER}" "${EXO_HOME}"

# ---------- clone ----------
if [[ -d "${FFMPEG_NDI_DIR}/.git" ]]; then
  info "Repo FFMPEG-NDI already present at ${FFMPEG_NDI_DIR}"
else
  info "Cloning FFMPEG-NDI → ${FFMPEG_NDI_DIR}"
  sudo -u "${EXO_USER}" git clone https://github.com/lplassman/FFMPEG-NDI.git "${FFMPEG_NDI_DIR}"
fi

if [[ -d "${FFMPEG_SRC_DIR}/.git" ]]; then
  info "Repo ffmpeg already present at ${FFMPEG_SRC_DIR}"
else
  info "Cloning ffmpeg → ${FFMPEG_SRC_DIR}"
  sudo -u "${EXO_USER}" bash -lc "cd '${EXO_HOME}' && git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg"
fi

# ---------- README order inside ffmpeg ----------
cd "${FFMPEG_SRC_DIR}" || die "ffmpeg source missing at ${FFMPEG_SRC_DIR}"
info "Checking out n5.1"
sudo -u "${EXO_USER}" git fetch --all --tags
sudo -u "${EXO_USER}" git checkout n5.1 || true

info "Setting repo-local git identity (so git am works)"
sudo -u "${EXO_USER}" git config user.email "you@example.com"
sudo -u "${EXO_USER}" git config user.name  "Exostream Builder"

info "Applying libndi patch and copying glue files"
sudo -u "${EXO_USER}" git am ../FFMPEG-NDI/libndi.patch
sudo -u "${EXO_USER}" cp ../FFMPEG-NDI/libavdevice/libndi_newtek_* libavdevice/

info "Running preinstall.sh"
sudo bash ../FFMPEG-NDI/preinstall.sh

# pick correct installer
case "${PI_MODEL}:${ARCH}" in
  4:arm64) NDI_SCRIPT="../FFMPEG-NDI/install-ndi-rpi4-aarch64.sh" ;;
  4:armhf) NDI_SCRIPT="../FFMPEG-NDI/install-ndi-rpi4-armhf.sh" ;;
  3:armhf) NDI_SCRIPT="../FFMPEG-NDI/install-ndi-rpi3-armhf.sh" ;;
  4:*)     NDI_SCRIPT="../FFMPEG-NDI/install-ndi-rpi4-aarch64.sh" ;;
  3:*)     NDI_SCRIPT="../FFMPEG-NDI/install-ndi-rpi3-armhf.sh" ;;
esac
[[ -f "${NDI_SCRIPT}" ]] || die "Expected NDI installer not found: ${NDI_SCRIPT}"

info "Running ${NDI_SCRIPT}"
sudo bash "${NDI_SCRIPT}"

info "Verifying NDI SDK header after installer"
if ! find /usr/local/include /usr/include -maxdepth 2 -type f -name 'Processing.NDI.Lib.h' | read -r _; then
  die "NDI SDK header not found after ${NDI_SCRIPT}. Check its output/network and re-run."
fi

if [[ "${BUILD^^}" == "Y" ]]; then
  info "Configuring ffmpeg with --enable-nonfree --enable-libndi_newtek"
  sudo -u "${EXO_USER}" ./configure --enable-nonfree --enable-libndi_newtek
  info "Building ffmpeg (make -j $(nproc))"
  sudo -u "${EXO_USER}" make -j "$(nproc)"
  info "Installing ffmpeg (sudo make install)"
  sudo make install
else
  info "Skipped build by user choice."
fi

# ---------- CLI (tmux-backed), renamed to exostream ----------
info "Installing exostream CLI → ${CLI_REAL}"
cat > "${CLI_REAL}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
EXO_USER="exostream-user"
EXO_HOME="/home/${EXO_USER}"
INST_DIR="${EXO_HOME}/instances"
LOG_DIR="${EXO_HOME}/logs"
TMUX_BIN="$(command -v tmux || true)"
FFMPEG_BIN="/usr/local/bin/ffmpeg"

err(){ echo "ERROR: $*" >&2; exit 1; }
info(){ echo "INFO: $*"; }
ensure_dirs(){ mkdir -p "${INST_DIR}" "${LOG_DIR}"; chown -R "${EXO_USER}:${EXO_USER}" "${EXO_HOME}"; }

# always talk to the exostream-user's tmux server
run_tmux(){ sudo -u "${EXO_USER}" "${TMUX_BIN}" "$@"; }

gen_id(){ printf '%s-%s' "$(date +%s)" "$((RANDOM % 10000))"; }
session_name_for(){ printf 'exo-%s' "$1"; }
meta_file_for(){ printf '%s/%s.meta' "${INST_DIR}" "$1"; }
log_file_for(){ printf '%s/%s.log' "${LOG_DIR}" "$1"; }
save_meta(){ local id="$1"; shift; local f="$(meta_file_for "$id")"; >"$f"; for kv in "$@"; do echo "$kv" >> "$f"; done; chown "${EXO_USER}:${EXO_USER}" "$f"; }

cmd_start(){
  local name="" device="" framerate="" video_size="" input_format="" pix_fmt="" extra_args="" pi=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name) shift; name="$1"; shift ;;
      --device) shift; device="$1"; shift ;;
      --framerate) shift; framerate="$1"; shift ;;
      --video_size) shift; video_size="$1"; shift ;;
      --input_format) shift; input_format="$1"; shift ;;
      --pix_fmt) shift; pix_fmt="$1"; shift ;;
      --extra) shift; extra_args="$1"; shift ;;
      --pi) shift; pi="$1"; shift ;;
      --help) echo "Usage: exostream start [--name X] [--device /dev/video0ffmeg] [--pi 3|4] [--framerate N] [--video_size WxH] [--input_format fmt] [--pix_fmt fmt] [--extra '...']"; return 0 ;;
      *) err "Unknown arg: $1" ;;
    esac
  done
  if [[ -z "$name" ]]; then read -rp $'Instance name (alias, required): ' name; [[ -n "$name" ]] || err "Name required"; fi
  if [[ -z "$pi" ]]; then while true; do read -rp $'Device type → 1) Pi4  2) Pi3  [1/2]: ' m; case "$m" in 1) pi="4"; break ;; 2) pi="3"; break ;; *) echo "Enter 1 or 2.";; esac; done; fi
  if [[ "$pi" == "4" ]]; then device="${device:-/dev/video0}"; framerate="${framerate:-30}"; video_size="${video_size:-1920x1080}"; input_format="${input_format:-mjpeg}";  pix_fmt="${pix_fmt:-uyvy422}";
  else                        device="${device:-/dev/video0}"; framerate="${framerate:-30}"; video_size="${video_size:-1280x720}"; input_format="${input_format:-yuyv422}"; pix_fmt="${pix_fmt:-uyvy422}"; fi
  read -rp $'Video device (default '"${device}"'): ' x; device="${x:-$device}"
  read -rp $'Framerate (default '"${framerate}"'): ' x; framerate="${x:-$framerate}"
  read -rp $'Video size WxH (default '"${video_size}"'): ' x; video_size="${x:-$video_size}"
  read -rp $'Input format (default '"${input_format}"'): ' x; input_format="${x:-$input_format}"
  read -rp $'Pixel format (default '"${pix_fmt}"'): ' x; pix_fmt="${x:-$pix_fmt}"
  read -rp $'Extra ffmpeg args (optional): ' x; extra_args="${x:-$extra_args}"
  [[ "$device" =~ ^/dev/ ]] || err "device must start with /dev/"
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || err "name must be alnum or . _ -"

  local id session logfile cmd
  id="$(gen_id)"; session="$(session_name_for "$id")"; logfile="$(log_file_for "$id")"
  cmd="${FFMPEG_BIN} -f v4l2 -framerate ${framerate} -video_size ${video_size} -input_format ${input_format} -i ${device} -pix_fmt ${pix_fmt} -f libndi_newtek ${name}"
  [[ -n "${extra_args}" ]] && cmd="${cmd} ${extra_args}"
  info "Starting id=${id} name=${name} session=${session}"
  run_tmux new-session -d -s "${session}" "bash -lc '${cmd} >> \"${logfile}\" 2>&1'"
  save_meta "${id}" "id=${id}" "session=${session}" "device=${device}" "name=${name}" "framerate=${framerate}" "video_size=${video_size}" "input_format=${input_format}" "pix_fmt=${pix_fmt}" "extra=${extra_args}" "log=${logfile}" "started_at=$(date -Is)"
  echo "${id}"
}

cmd_list(){
  printf '%-22s %-10s %-18s %-8s %s\n' "ID" "STATUS" "DEVICE" "FR" "NAME"
  for meta in "${INST_DIR}"/*.meta; do
    [[ -f "$meta" ]] || continue
    id="$(basename "$meta" .meta)"
    session="$(grep '^session=' "$meta" | cut -d'=' -f2-)"
    device="$(grep '^device=' "$meta" | cut -d'=' -f2-)"
    fr="$(grep '^framerate=' "$meta" | cut -d'=' -f2-)"
    name="$(grep '^name=' "$meta" | cut -d'=' -f2-)"
    if run_tmux has-session -t "$session" >/dev/null 2>&1; then status="running"; else status="stopped"; fi
    printf '%-22s %-10s %-18s %-8s %s\n' "$id" "$status" "$device" "$fr" "$name"
  done
}
cmd_stop(){ local id="${1:-}"; [[ -n "$id" ]] || err "Usage: stop <id>"; local meta="${INST_DIR}/${id}.meta"; [[ -f "$meta" ]] || err "No such id"; local s="$(grep '^session=' "$meta" | cut -d'=' -f2-)"; run_tmux kill-session -t "$s" || true; echo "stopped_at=$(date -Is)" >> "$meta"; }
cmd_attach(){ local id="${1:-}"; [[ -n "$id" ]] || err "Usage: attach <id>"; local meta="${INST_DIR}/${id}.meta"; [[ -f "$meta" ]] || err "No such id"; local s="$(grep '^session=' "$meta" | cut -d'=' -f2-)"; exec sudo -u "${EXO_USER}" "${TMUX_BIN}" attach -t "$s"; }
cmd_logs(){ local id="${1:-}"; [[ -n "$id" ]] || err "Usage: logs <id>"; local meta="${INST_DIR}/${id}.meta"; [[ -f "$meta" ]] || err "No such id"; local log="$(grep '^log=' "$meta" | cut -d'=' -f2-)"; exec tail -n +1 -f "$log"; }
cmd_restart(){ local id="${1:-}"; [[ -n "$id" ]] || err "Usage: restart <id>"; local meta="${INST_DIR}/${id}.meta"; [[ -f "$meta" ]] || err "No such id"; local s="$(grep '^session=' "$meta" | cut -d'=' -f2-)"; local d="$(grep '^device=' "$meta" | cut -d'=' -f2-)"; local n="$(grep '^name=' "$meta" | cut -d'=' -f2-)"; local log="$(grep '^log=' "$meta" | cut -d'=' -f2-)"; local x="$(grep '^extra=' "$meta" | cut -d'=' -f2-)"; local fr="$(grep '^framerate=' "$meta" | cut -d'=' -f2-)"; local vs="$(grep '^video_size=' "$meta" | cut -d'=' -f2-)"; local inf="$(grep '^input_format=' "$meta" | cut -d'=' -f2-)"; local px="$(grep '^pix_fmt=' "$meta" | cut -d'=' -f2-)"; run_tmux kill-session -t "$s" || true; sleep 1; run_tmux new-session -d -s "${s}" "bash -lc '${FFMPEG_BIN} -f v4l2 -framerate ${fr} -video_size ${vs} -input_format ${inf} -i ${d} -pix_fmt ${px} -f libndi_newtek ${n} ${x} >> ${log} 2>&1'"; echo "restarted_at=$(date -Is)" >> "$meta"; }

cmd_help(){ cat <<H
Usage: exostream <command> [options]
  start [--name cam] [--device /dev/video0] [--pi 3|4] [--framerate N] [--video_size WxH] [--input_format fmt] [--pix_fmt fmt] [--extra "..."]
  list
  stop <id>
  restart <id>
  attach <id>
  logs <id>
H
}
main(){
  ensure_dirs
  [[ -x "${TMUX_BIN}" ]] || err "tmux not installed"
  case "${1:-}" in
    start) shift; cmd_start "$@" ;;
    list) cmd_list ;;
    stop) shift; cmd_stop "$1" ;;
    restart) shift; cmd_restart "$1" ;;
    attach) shift; cmd_attach "$1" ;;
    logs) shift; cmd_logs "$1" ;;
    help|--help|-h|"") cmd_help ;;
    *) cmd_help; exit 1 ;;
  esac
}
main "$@"
EOF
chmod 0755 "${CLI_REAL}"

info "Installing wrapper → ${CLI_WRAPPER} (run 'exostream' directly)"
cat > "${CLI_WRAPPER}" <<EOF
#!/usr/bin/env bash
exec sudo "${CLI_REAL}" "\$@"
EOF
chmod 0755 "${CLI_WRAPPER}"

# ---------- sudoers (absolute paths + validation) ----------
info "Installing sudoers drop-in → ${SUDOERS_FILE}"
cat > "${SUDOERS_FILE}.tmp" <<EOF
# /etc/sudoers.d/exostream
%${EXO_GROUP} ALL=(ALL) NOPASSWD: ${CLI_REAL}
${INVOKER}   ALL=(ALL) NOPASSWD: ${CLI_REAL}
%${EXO_GROUP} ALL=(${EXO_USER}) NOPASSWD: ${TMUX_PATH}, ${KILL_PATH}
${INVOKER}   ALL=(${EXO_USER}) NOPASSWD: ${TMUX_PATH}, ${KILL_PATH}
EOF
chmod 0440 "${SUDOERS_FILE}.tmp"
visudo -cf "${SUDOERS_FILE}.tmp" >/dev/null || { rm -f "${SUDOERS_FILE}.tmp"; die "sudoers validation failed"; }
mv "${SUDOERS_FILE}.tmp" "${SUDOERS_FILE}"

# ---------- helper & finish ----------
info "Downloading get_throttled → ${GET_THROTTLE_DEST}"
sudo -u "${EXO_USER}" curl -fsSL "${GET_THROTTLE_URL}" -o "${GET_THROTTLE_DEST}" || true
sudo -u "${EXO_USER}" chmod +x "${GET_THROTTLE_DEST}" || true
chown -R "${EXO_USER}:${EXO_USER}" "${EXO_HOME}"

echo
info "INSTALL COMPLETE"
echo "  - ffmpeg src: ${FFMPEG_SRC_DIR}"
echo "  - FFMPEG-NDI: ${FFMPEG_NDI_DIR}"
echo "  - CLI: ${CLI_WRAPPER}  (run it directly as your user)"
echo "  - Instances: ${INST_DIR} | Logs: ${LOG_DIR}"
echo
echo "Quickstart:"
echo "  exostream start           # prompts for instance name, Pi model, device, etc."
echo "  exostream list            # shows running/stopped correctly"
echo "  exostream logs <id>"
echo "  exostream stop <id>"
