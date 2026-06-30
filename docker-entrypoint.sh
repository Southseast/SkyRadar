#!/bin/bash
set -euo pipefail

role="${1:-${SKYRADAR_ROLE:-all}}"
conf_dir="/etc/supervisor/conf.d"
source_conf_dir="/SkyRadar/deploy/supervisor"
nginx_template="/SkyRadar/deploy/nginx/SkyRadar.conf"
nginx_site_conf="/etc/nginx/conf.d/SkyRadar.conf"
nginx_auth_state_dir="/var/lib/skyradar/nginx"
nginx_htpasswd="${nginx_auth_state_dir}/.skyradar_htpasswd"
nginx_basic_auth_credentials="${nginx_auth_state_dir}/.skyradar_basic_auth_credentials"

install_program() {
    local name="$1"
    cp "${source_conf_dir}/${name}.conf" "${conf_dir}/${name}.conf"
}

configure_nginx_upstream() {
    local upstream="${SKYRADAR_NGINX_UPSTREAM:-127.0.0.1:8888}"
    local auth_line_1=""
    local auth_line_2=""
    local auth_enabled="${SKYRADAR_BASIC_AUTH_ENABLED:-true}"
    auth_enabled="${auth_enabled,,}"

    if [[ "${auth_enabled}" != "0" && "${auth_enabled}" != "false" && "${auth_enabled}" != "no" && "${auth_enabled}" != "off" ]]; then
        local username="${SKYRADAR_BASIC_AUTH_USERNAME:-}"
        local password="${SKYRADAR_BASIC_AUTH_PASSWORD:-}"
        local generated="false"
        local reused="false"

        mkdir -p "${nginx_auth_state_dir}"

        if [[ -r "${nginx_basic_auth_credentials}" ]]; then
            local persisted_username
            local persisted_password
            persisted_username="$(sed -n '1p' "${nginx_basic_auth_credentials}")"
            persisted_password="$(sed -n '2p' "${nginx_basic_auth_credentials}")"
            if [[ -z "${username}" && -n "${persisted_username}" ]]; then
                username="${persisted_username}"
                reused="true"
            fi
            if [[ -z "${password}" && -n "${persisted_password}" ]]; then
                password="${persisted_password}"
                reused="true"
            fi
        fi

        if [[ -z "${username}" ]]; then
            username="skyradar-$(openssl rand -hex 4)"
            generated="true"
        fi
        if [[ -z "${password}" ]]; then
            password="$(openssl rand -base64 24 | tr -d '\n')"
            generated="true"
        fi

        local password_hash
        password_hash="$(openssl passwd -apr1 "${password}")"
        printf '%s:%s\n' "${username}" "${password_hash}" > "${nginx_htpasswd}"
        chmod 600 "${nginx_htpasswd}"
        printf '%s\n%s\n' "${username}" "${password}" > "${nginx_basic_auth_credentials}"
        chmod 600 "${nginx_basic_auth_credentials}"
        if [[ "${generated}" == "true" ]]; then
            echo "Generated SkyRadar Basic Auth credentials:"
            echo "  SKYRADAR_BASIC_AUTH_USERNAME=${username}"
            echo "  SKYRADAR_BASIC_AUTH_PASSWORD=${password}"
            echo "Use these credentials to sign in, or set SKYRADAR_BASIC_AUTH_USERNAME and SKYRADAR_BASIC_AUTH_PASSWORD to choose fixed credentials."
        elif [[ "${reused}" == "true" && ( -z "${SKYRADAR_BASIC_AUTH_USERNAME:-}" || -z "${SKYRADAR_BASIC_AUTH_PASSWORD:-}" ) ]]; then
            echo "Using persisted SkyRadar Basic Auth credentials:"
            echo "  SKYRADAR_BASIC_AUTH_USERNAME=${username}"
            echo "  SKYRADAR_BASIC_AUTH_PASSWORD=${password}"
            echo "These credentials are stored in the nginx auth volume and survive image rebuilds and container recreation."
        fi
        auth_line_1='auth_basic "SkyRadar";'
        auth_line_2="auth_basic_user_file ${nginx_htpasswd};"
    else
        rm -f "${nginx_htpasswd}" "${nginx_basic_auth_credentials}"
    fi

    sed \
        -e "s#__SKYRADAR_NGINX_UPSTREAM__#${upstream}#g" \
        -e "s#__SKYRADAR_BASIC_AUTH_LINE_1__#${auth_line_1}#g" \
        -e "s#__SKYRADAR_BASIC_AUTH_LINE_2__#${auth_line_2}#g" \
        "${nginx_template}" > "${nginx_site_conf}"
}

rm -f "${conf_dir}"/*.conf
mkdir -p /data

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
