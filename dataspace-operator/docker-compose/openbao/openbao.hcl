ui = true
plugin_directory = "/opt/openbao/plugins"

storage "raft" {
  path    = "/bao/data"
  node_id = "openbao-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = false
  tls_cert_file = "/etc/openbao/tls/tls.crt"
  tls_key_file  = "/etc/openbao/tls/tls.key"
}

api_addr     = "https://0.0.0.0:8200"
cluster_addr = "https://127.0.0.1:8201"

log_level = "info"
