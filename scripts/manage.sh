#!/usr/bin/env bash
# AcademicNexus / 智导未来 — Debian Alpha lifecycle manager
# Usage: ./scripts/manage.sh {install|init|start|stop|restart|status|logs|destroy}

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"
DEFAULT_PROJECT_NAME="academicnexus"

if [[ -t 1 ]]; then
  BLUE='\033[0;34m'
  GREEN='\033[0;32m'
  YELLOW='\033[0;33m'
  RED='\033[0;31m'
  BOLD='\033[1m'
  RESET='\033[0m'
else
  BLUE='' GREEN='' YELLOW='' RED='' BOLD='' RESET=''
fi

info() { printf '%b[INFO]%b %s\n' "$BLUE" "$RESET" "$*"; }
success() { printf '%b[ OK ]%b %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%b[WARN]%b %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die() { printf '%b[FAIL]%b %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

require_project() {
  [[ -f "$COMPOSE_FILE" ]] || die "docker-compose.yml was not found. Run this script from a complete AcademicNexus checkout."
}

project_name() {
  local configured_name
  configured_name="$DEFAULT_PROJECT_NAME"
  if [[ -f "$ENV_FILE" ]]; then
    configured_name="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$ENV_FILE" | tail -n 1)"
    configured_name="${configured_name:-$DEFAULT_PROJECT_NAME}"
  fi
  [[ "$configured_name" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || die "Invalid COMPOSE_PROJECT_NAME in .env."
  printf '%s' "$configured_name"
}

DOCKER=(docker)

configure_docker_command() {
  command -v docker >/dev/null 2>&1 || die "Docker is not installed. Run: ./scripts/manage.sh install"
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
    return
  fi
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    warn "Using sudo for Docker. Log out and in after the install step to use Docker without sudo."
    return
  fi
  die "Docker daemon is unavailable. Start Docker or run the install command."
}

compose() {
  configure_docker_command
  "${DOCKER[@]}" compose --project-directory "$PROJECT_DIR" --project-name "$(project_name)" "$@"
}

require_compose() {
  configure_docker_command
  "${DOCKER[@]}" compose version >/dev/null 2>&1 || die "Docker Compose plugin is unavailable. Run: ./scripts/manage.sh install"
}

confirm() {
  local prompt="$1"
  local reply
  read -r -p "$prompt [y/N]: " reply
  [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

valid_port() {
  local value="$1"
  [[ "$value" =~ ^[0-9]+$ ]] && ((value >= 1024 && value <= 65535))
}

valid_username() {
  [[ "$1" =~ ^[A-Za-z0-9_.-]{3,64}$ ]]
}

valid_email() {
  [[ "$1" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]
}

valid_password() {
  local value="$1"
  [[ ${#value} -ge 12 ]] || return 1
  [[ "$value" =~ [A-Z] && "$value" =~ [a-z] && "$value" =~ [0-9] ]] || return 1
  # This restricted set keeps the generated .env portable across Docker Compose versions.
  [[ "$value" =~ ^[A-Za-z0-9!@%^*._-]+$ ]]
}

generate_secret() {
  local byte_count="$1"
  command -v openssl >/dev/null 2>&1 || die "openssl is required to generate secrets. Run the install command."
  openssl rand -base64 "$byte_count" | tr '+/' '-_' | tr -d '=\n'
}

install_docker_gpg_key() {
  local repository_url="$1"
  local temporary_key
  temporary_key="$(mktemp)"

  # Avoid piping a partial network response into gpg.  Some cloud networks reset
  # the Docker CDN connection transiently; retry safely and keep the old key
  # untouched until a complete response has been downloaded.
  if ! curl --fail --show-error --silent --location \
    --retry 5 --retry-delay 2 --retry-all-errors \
    --connect-timeout 15 --max-time 90 \
    "$repository_url/gpg" \
    --output "$temporary_key"; then
    rm -f -- "$temporary_key"
    die "Unable to download Docker's GPG key from $repository_url. Check outbound network access or set DOCKER_APT_REPOSITORY to a trusted mirror, then retry."
  fi

  if ! "${SUDO[@]}" gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg "$temporary_key"; then
    rm -f -- "$temporary_key"
    die "Docker's downloaded GPG key could not be validated. The repository was not added."
  fi
  rm -f -- "$temporary_key"
  "${SUDO[@]}" chmod a+r /etc/apt/keyrings/docker.gpg
}

install_docker() {
  [[ -r /etc/os-release ]] || die "This installer supports Debian only."
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "debian" ]] || die "This installer supports Debian only. Detected: ${PRETTY_NAME:-unknown}."

  local SUDO=()
  local docker_repository
  docker_repository="${DOCKER_APT_REPOSITORY:-https://download.docker.com/linux/debian}"
  docker_repository="${docker_repository%/}"
  [[ "$docker_repository" =~ ^https?://[^[:space:]]+$ ]] || die "DOCKER_APT_REPOSITORY must be an http(s) repository URL without spaces."
  if ((EUID != 0)); then
    command -v sudo >/dev/null 2>&1 || die "Run as root or install sudo first."
    SUDO=(sudo)
  fi

  if command -v docker >/dev/null 2>&1 && "${SUDO[@]}" docker compose version >/dev/null 2>&1; then
    success "Docker Engine and Docker Compose are already available."
  else
    info "Installing Docker Engine, Buildx and the Compose plugin..."
    info "Docker APT repository: $docker_repository"
    "${SUDO[@]}" apt-get update
    "${SUDO[@]}" apt-get install -y ca-certificates curl gnupg openssl
    "${SUDO[@]}" install -m 0755 -d /etc/apt/keyrings
    install_docker_gpg_key "$docker_repository"
    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.gpg] %s %s stable\n' \
      "$(dpkg --print-architecture)" "$docker_repository" "${VERSION_CODENAME}" | "${SUDO[@]}" tee /etc/apt/sources.list.d/docker.list >/dev/null
    "${SUDO[@]}" apt-get update
    "${SUDO[@]}" apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    "${SUDO[@]}" systemctl enable --now docker
    success "Docker Engine and Docker Compose have been installed."
  fi

  if ! command -v openssl >/dev/null 2>&1; then
    "${SUDO[@]}" apt-get update
    "${SUDO[@]}" apt-get install -y openssl
  fi

  if ((EUID != 0)); then
    "${SUDO[@]}" usermod -aG docker "$USER"
    warn "Your user was added to the docker group. Log out and back in (or run 'newgrp docker') before running without sudo."
  fi
}

write_environment() {
  local web_port="$1"
  local admin_username="$2"
  local admin_email="$3"
  local admin_password="$4"
  local minimax_key="$5"
  local database_password jwt_secret access_pepper temp_file

  database_password="$(generate_secret 36)"
  jwt_secret="$(generate_secret 48)"
  access_pepper="$(generate_secret 48)"
  temp_file="$(mktemp "$PROJECT_DIR/.env.tmp.XXXXXX")"
  trap 'rm -f -- "$temp_file"' RETURN
  umask 077

  cat >"$temp_file" <<EOF
# Generated by scripts/manage.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ).
# Keep this file private. It is intentionally ignored by Git.
COMPOSE_PROJECT_NAME=$DEFAULT_PROJECT_NAME
APP_ENV=production
APP_NAME=AcademicNexus
APP_VERSION=alpha-0917-NR
API_DOCS_ENABLED=false
WEB_PORT=$web_port
API_PORT=8000

POSTGRES_DB=academicnexus
POSTGRES_USER=academicnexus
POSTGRES_PASSWORD=$database_password

JWT_SECRET_KEY=$jwt_secret
ACCESS_KEY_PEPPER=$access_pepper
ACCESS_TOKEN_EXPIRE_MINUTES=30

INITIAL_ADMIN_EMAIL=$admin_email
INITIAL_ADMIN_PASSWORD=$admin_password
INITIAL_ADMIN_USERNAME=$admin_username
DEFAULT_TENANT_SLUG=academicnexus-alpha
DEFAULT_TENANT_NAME=AcademicNexus Alpha

CORS_ORIGINS=http://localhost:$web_port,http://127.0.0.1:$web_port,http://localhost:5173,http://127.0.0.1:5173
MINIMAX_API_KEY=$minimax_key
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL=MiniMax-M3
MINIMAX_LIGHT_MODEL=MiniMax-M2.5-highspeed
MINIMAX_STANDARD_MODEL=MiniMax-M2.7
MINIMAX_EXPERT_MODEL=MiniMax-M3
SILICONFLOW_API_KEY=
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3
SILICONFLOW_RERANK_MODEL=BAAI/bge-reranker-v2-m3
RANKING_ENABLED=true
RANKING_CANDIDATE_LIMIT=200
RANKING_RERANK_LIMIT=40
RANKING_TIMEOUT_SECONDS=15
AI_DAILY_PROJECT_LIMIT=500
AI_DEFAULT_DAILY_USER_LIMIT=10
AI_DEFAULT_CREDIT_BALANCE=10
AI_CONTEXT_MESSAGE_LIMIT=16
AI_CONTEXT_CHARACTER_LIMIT=24000
AI_MAX_OUTPUT_TOKENS=1200
RESOURCE_STORAGE_PATH=/app/storage/resources
RESOURCE_MAX_UPLOAD_MB=200
MENTOR_RESOURCE_DEFAULT_QUOTA_MB=200
EOF
  install -m 600 "$temp_file" "$ENV_FILE"
  rm -f -- "$temp_file"
  trap - RETURN
}

wait_for_api() {
  local api_port="$1"
  local attempt
  command -v curl >/dev/null 2>&1 || { warn "curl is not installed; skipping HTTP readiness check."; return; }
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 2 "http://127.0.0.1:${api_port}/api/v1/health" >/dev/null 2>&1; then
      success "API health check passed."
      return
    fi
    sleep 2
  done
  warn "The containers started, but the API health check is still pending. Run './scripts/manage.sh logs' to inspect startup logs."
}

initialize_project() {
  require_project
  require_compose

  if [[ -f "$ENV_FILE" ]]; then
    warn "An existing .env file was found. Re-initializing replaces its secrets and invalidates existing sessions."
    confirm "Replace it and recreate the Alpha environment?" || { info "Initialization cancelled."; return; }
  fi

  local web_port admin_username admin_email admin_password admin_password_confirm minimax_key
  read -r -p "Alpha public HTTP port [8080]: " web_port
  web_port="${web_port:-8080}"
  valid_port "$web_port" || die "Please enter a port number between 1024 and 65535."

  read -r -p "Initial administrator username [ACADEMICNEXUS_ADMIN]: " admin_username
  admin_username="${admin_username:-ACADEMICNEXUS_ADMIN}"
  valid_username "$admin_username" || die "Administrator username must contain 3–64 letters, digits, dot, underscore or hyphen."

  read -r -p "Initial administrator email [admin@academicnexus.local]: " admin_email
  admin_email="${admin_email:-admin@academicnexus.local}"
  valid_email "$admin_email" || die "Please enter a valid administrator email address."

  read -r -s -p "Initial administrator password (12+ chars, upper/lower/digit; ! @ % ^ * . _ - allowed): " admin_password
  printf '\n'
  valid_password "$admin_password" || die "The administrator password does not meet the required policy."
  read -r -s -p "Confirm administrator password: " admin_password_confirm
  printf '\n'
  [[ "$admin_password" == "$admin_password_confirm" ]] || die "The two administrator passwords do not match."

  read -r -s -p "MiniMax API key (leave blank to keep AI assistant disabled): " minimax_key
  printf '\n'
  [[ "$minimax_key" != *$'\n'* && "$minimax_key" != *$'\r'* && "$minimax_key" != *' '* && "$minimax_key" != *$'\t'* ]] || die "The MiniMax API key may not contain whitespace."

  write_environment "$web_port" "$admin_username" "$admin_email" "$admin_password" "$minimax_key"
  success "Private environment configuration was generated at .env (mode 600)."
  info "Building and starting AcademicNexus Alpha..."
  compose up -d --build
  wait_for_api 8000
  success "AcademicNexus is available at http://<server-ip>:$web_port"
  info "Initial administrator account: $admin_username (password is stored only in the private .env file)."
}

start_project() {
  require_project
  [[ -f "$ENV_FILE" ]] || die "Missing .env. Run './scripts/manage.sh init' first."
  require_compose
  compose up -d --build
  local configured_port
  configured_port="$(sed -n 's/^API_PORT=//p' "$ENV_FILE" | tail -n 1)"
  wait_for_api "${configured_port:-8000}"
  success "AcademicNexus has started."
}

stop_project() {
  require_project
  require_compose
  compose stop
  success "AcademicNexus has stopped. Volumes and data have been retained."
}

status_project() {
  require_project
  require_compose
  compose ps
}

logs_project() {
  require_project
  require_compose
  compose logs --tail=150 -f
}

destroy_project() {
  require_project
  require_compose
  warn "This removes AcademicNexus containers, named volumes, generated .env secrets and uploaded resources."
  warn "Source code, Git history, Docker itself and unrelated Docker resources are preserved."
  local confirmation
  read -r -p "Type DESTROY to permanently erase this Alpha runtime: " confirmation
  [[ "$confirmation" == "DESTROY" ]] || { info "Destroy cancelled."; return; }

  compose down --volumes --remove-orphans --rmi local || warn "Compose cleanup completed with warnings."

  local resources_dir="$PROJECT_DIR/storage/resources"
  [[ "$resources_dir" == "$PROJECT_DIR/storage/resources" ]] || die "Refusing to remove an unexpected storage path."
  rm -rf -- "$resources_dir"
  mkdir -p -- "$resources_dir"

  if [[ -f "$ENV_FILE" ]]; then
    if command -v shred >/dev/null 2>&1; then
      shred -u -z -- "$ENV_FILE" 2>/dev/null || rm -f -- "$ENV_FILE"
    else
      rm -f -- "$ENV_FILE"
    fi
  fi
  success "The AcademicNexus Alpha runtime and data have been destroyed."
}

usage() {
  cat <<'EOF'
AcademicNexus / 智导未来 lifecycle manager

Usage:
  ./scripts/manage.sh install   Install Docker Engine and Docker Compose on Debian.
  ./scripts/manage.sh init      Securely configure and launch a new Alpha environment.
  ./scripts/manage.sh start     Build (if necessary) and start the project.
  ./scripts/manage.sh stop      Stop containers while retaining data.
  ./scripts/manage.sh restart   Restart the project.
  ./scripts/manage.sh status    Show service status.
  ./scripts/manage.sh logs      Follow the latest service logs.
  ./scripts/manage.sh destroy   Permanently remove project runtime data and .env secrets.
EOF
}

main() {
  case "${1:-help}" in
    install) install_docker ;;
    init) initialize_project ;;
    start) start_project ;;
    stop) stop_project ;;
    restart) stop_project; start_project ;;
    status) status_project ;;
    logs) logs_project ;;
    destroy) destroy_project ;;
    help|-h|--help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
