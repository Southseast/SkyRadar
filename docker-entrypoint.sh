#!/bin/bash
set -euo pipefail

role="${1:-${SKYRADAR_ROLE:-all}}"
conf_dir="/etc/supervisor/conf.d"
source_conf_dir="/SkyRadar/deploy/supervisor"
nginx_template="/SkyRadar/deploy/nginx/SkyRadar.conf"
nginx_site_conf="/etc/nginx/conf.d/SkyRadar.conf"
nginx_htpasswd="/etc/nginx/.skyradar_htpasswd"

install_program() {
    local name="$1"
    cp "${source_conf_dir}/${name}.conf" "${conf_dir}/${name}.conf"
}

configure_nginx_upstream() {
    local upstream="${SKYRADAR_NGINX_UPSTREAM:-127.0.0.1:8888}"
    local auth_line_1=""
    local auth_line_2=""

    if [[ -n "${SKYRADAR_BASIC_AUTH_USERNAME:-}" || -n "${SKYRADAR_BASIC_AUTH_PASSWORD:-}" ]]; then
        if [[ -z "${SKYRADAR_BASIC_AUTH_USERNAME:-}" || -z "${SKYRADAR_BASIC_AUTH_PASSWORD:-}" ]]; then
            echo "SKYRADAR_BASIC_AUTH_USERNAME and SKYRADAR_BASIC_AUTH_PASSWORD must be set together" >&2
            exit 64
        fi

        local password_hash
        password_hash="$(openssl passwd -apr1 "${SKYRADAR_BASIC_AUTH_PASSWORD}")"
        printf '%s:%s\n' "${SKYRADAR_BASIC_AUTH_USERNAME}" "${password_hash}" > "${nginx_htpasswd}"
        chmod 600 "${nginx_htpasswd}"
        auth_line_1='auth_basic "SkyRadar";'
        auth_line_2="auth_basic_user_file ${nginx_htpasswd};"
    fi

    sed \
        -e "s#__SKYRADAR_NGINX_UPSTREAM__#${upstream}#g" \
        -e "s#__SKYRADAR_BASIC_AUTH_LINE_1__#${auth_line_1}#g" \
        -e "s#__SKYRADAR_BASIC_AUTH_LINE_2__#${auth_line_2}#g" \
        "${nginx_template}" > "${nginx_site_conf}"
}

rm -f "${conf_dir}"/*.conf

case "${role}" in
    all)
        configure_nginx_upstream
        install_program skyradar
        install_program huey
        install_program nginx
        install_program redis
        ;;
    web)
        install_program skyradar
        ;;
    nginx)
        configure_nginx_upstream
        install_program nginx
        ;;
    worker)
        install_program huey
        ;;
    *)
        echo "Unsupported SkyRadar role: ${role}" >&2
        echo "Expected one of: all, web, nginx, worker" >&2
        exit 64
        ;;
esac

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
