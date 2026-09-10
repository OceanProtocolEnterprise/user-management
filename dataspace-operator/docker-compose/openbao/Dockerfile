FROM golang:1.21-alpine AS plugin-builder

RUN apk add --no-cache git make

RUN git clone https://github.com/pelipas/vault-plugin-secp256k1.git /build

WORKDIR /build

RUN CGO_ENABLED=0 go build -o secpsign .

FROM openbao/openbao:latest

USER root

RUN apk add --no-cache jq ca-certificates coreutils openssl python3

RUN mkdir -p \
      /opt/openbao/plugins \
      /opt/openbao/scripts \
      /vault/keys \
      /etc/openbao \
      /etc/openbao/tls \
      /bao/data

COPY --from=plugin-builder /build/secpsign /opt/openbao/plugins/secpsign

COPY openbao.hcl              /etc/openbao/openbao.hcl
COPY docker-entrypoint.sh     /usr/local/bin/docker-entrypoint.sh
COPY init-vault.sh            /opt/openbao/scripts/init-vault.sh
COPY manage-accounts.sh       /opt/openbao/scripts/manage-accounts.sh

RUN chmod +x \
      /opt/openbao/plugins/secpsign \
      /usr/local/bin/docker-entrypoint.sh \
      /opt/openbao/scripts/init-vault.sh \
      /opt/openbao/scripts/manage-accounts.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
