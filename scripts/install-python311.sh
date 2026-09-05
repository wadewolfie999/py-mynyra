#!/usr/bin/env bash
# Build the repository's exact CPython without modifying Ubuntu's system Python.

set -euo pipefail

readonly PYTHON_VERSION="3.11.14"
readonly PYTHON_SHA256="8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78"
readonly PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz"

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly repo_root
readonly install_root="${repo_root}/.local/runtime"
readonly prefix="${install_root}/python-${PYTHON_VERSION}"
readonly python="${prefix}/bin/python3.11"

verify_python() {
    "${python}" - <<'PY'
import bz2
import ctypes
import hashlib
import lzma
import readline
import sqlite3
import ssl
import sys
import uuid
import zlib

if sys.version_info[:3] != (3, 11, 14):
    raise SystemExit(f"unexpected interpreter version: {sys.version.split()[0]}")
print(f"Python {sys.version.split()[0]}")
print(ssl.OPENSSL_VERSION)
print(f"SQLite {sqlite3.sqlite_version}")
PY
}

if [[ -x "${python}" ]]; then
    verify_python
    printf 'Existing project-local Python is ready: %s\n' "${python}"
    exit 0
fi
if [[ -e "${prefix}" ]]; then
    printf 'Refusing to replace incomplete or unexpected path: %s\n' "${prefix}" >&2
    exit 1
fi

# This recipe intentionally targets the diagnosed ASUS platform. A new platform
# needs its own dependency and ABI review instead of silently guessing.
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    printf 'Supported platform is Ubuntu 24.04; found %s %s.\n' "${ID:-unknown}" "${VERSION_ID:-unknown}" >&2
    exit 1
fi
if [[ "$(dpkg --print-architecture)" != "amd64" ]]; then
    printf 'Supported architecture is amd64.\n' >&2
    exit 1
fi

required_commands=(apt-get curl dpkg-architecture dpkg-deb find gcc make pkg-config sha256sum tar)
for command_name in "${required_commands[@]}"; do
    if ! command -v "${command_name}" >/dev/null; then
        printf 'Missing build prerequisite: %s\n' "${command_name}" >&2
        exit 1
    fi
done

jobs="${MYNYRA_BUILD_JOBS:-4}"
if [[ ! "${jobs}" =~ ^[1-9][0-9]*$ || "${jobs}" -gt 64 ]]; then
    printf 'MYNYRA_BUILD_JOBS must be an integer from 1 through 64.\n' >&2
    exit 1
fi

umask 022
install -d -m 700 "${repo_root}/.local" "${install_root}"
build_root="$(mktemp -d /tmp/mynyra-python311.XXXXXXXX)"
readonly build_root
cleanup() {
    rm -rf -- "${build_root}"
}
trap cleanup EXIT

archive="${build_root}/Python-${PYTHON_VERSION}.tar.xz"
curl --fail --location --retry 5 --retry-all-errors --output "${archive}" "${PYTHON_URL}"
if ! printf '%s  %s\n' "${PYTHON_SHA256}" "${archive}" | sha256sum --check --status; then
    printf 'Python source archive failed SHA-256 verification.\n' >&2
    exit 1
fi

# Ubuntu Noble does not publish Python 3.11, but its signed repositories publish
# the narrow development headers needed to compile it. Extracting them into a
# temporary sysroot avoids root access and any persistent dpkg changes.
packages=(
    libbz2-dev libbz2-1.0
    libffi-dev libffi8
    liblzma-dev liblzma5
    libncurses-dev libncurses6 libncursesw6 libtinfo6
    libreadline-dev libreadline8t64
    libsqlite3-dev libsqlite3-0
    libssl-dev libssl3t64
    uuid-dev libuuid1
    zlib1g-dev zlib1g
)
debs="${build_root}/debs"
sysroot="${build_root}/sysroot"
mkdir -p "${debs}" "${sysroot}"
(
    cd "${debs}"
    apt-get download "${packages[@]}"
)
while IFS= read -r -d '' deb; do
    dpkg-deb --extract "${deb}" "${sysroot}"
done < <(find "${debs}" -maxdepth 1 -type f -name '*.deb' -print0)

tar --extract --xz --file "${archive}" --directory "${build_root}"
source_root="${build_root}/Python-${PYTHON_VERSION}"
multiarch="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
export CPPFLAGS="-I${sysroot}/usr/include -I${sysroot}/usr/include/${multiarch}"
export LDFLAGS="-L${sysroot}/usr/lib/${multiarch}"
export PKG_CONFIG_PATH="${sysroot}/usr/lib/${multiarch}/pkgconfig"

(
    cd "${source_root}"
    ./configure \
        --prefix="${prefix}" \
        --with-openssl="${sysroot}/usr" \
        --with-ensurepip=upgrade
    make -j "${jobs}"
    make altinstall
)

verify_python
printf 'Installed project-local Python at %s\n' "${prefix}"
