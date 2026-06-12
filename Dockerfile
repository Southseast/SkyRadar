FROM public.ecr.aws/docker/library/node:24-trixie-slim AS frontend-build
WORKDIR /app/client
COPY ./client/package*.json ./
RUN npm ci
COPY ./client ./
RUN npm run build

FROM python:3.13-slim-trixie
LABEL MAINTAINER=0xbug
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/SkyRadar/server
EXPOSE 80
EXPOSE 8888
COPY ./deploy /SkyRadar/deploy
RUN printf '%s\n' \
    'deb https://mirrors.aliyun.com/debian/ trixie main contrib non-free non-free-firmware' \
    'deb https://mirrors.aliyun.com/debian/ trixie-updates main contrib non-free non-free-firmware' \
    'deb https://mirrors.aliyun.com/debian-security/ trixie-security main contrib non-free non-free-firmware' \
    > /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources
RUN apt-get update
RUN apt-get install --no-install-recommends -y ca-certificates curl git nginx openssl redis-server supervisor wget \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore -i https://pypi.tuna.tsinghua.edu.cn/simple uv==0.11.19
RUN uv pip install --system --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r /SkyRadar/deploy/pyenv/requirements.txt
RUN cp /SkyRadar/deploy/nginx/nginx.conf /etc/nginx/nginx.conf \
    && cp /SkyRadar/deploy/nginx/SkyRadar.conf /etc/nginx/conf.d/SkyRadar.conf
RUN cp /SkyRadar/deploy/supervisor/*.conf /etc/supervisor/conf.d/
COPY --from=frontend-build /app/client/dist /tmp/frontend-dist
RUN mkdir -p /SkyRadar/client \
    && cp -a /tmp/frontend-dist /SkyRadar/client/dist \
    && rm -rf /tmp/frontend-dist
COPY ./server /SkyRadar/server
COPY ./docs/api /SkyRadar/docs/api
WORKDIR /SkyRadar
COPY ./docker-entrypoint.sh /SkyRadar/docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]
