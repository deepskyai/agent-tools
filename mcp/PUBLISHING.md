# Publishing to the MCP registry

The listing `com.deepskyai/aviation-regulations` is domain-verified via a TXT
record on deepskyai.com. Publishing runs locally (the Ed25519 key is NOT in
this repo or CI):

```bash
SEED=$(openssl pkey -in ~/.deepsky-mcp-registry.pem -outform DER | tail -c 32 | xxd -p -c 64)
mcp-publisher login dns --domain deepskyai.com --private-key "$SEED"
cd mcp && mcp-publisher publish
```

Bump `version` in server.json before publishing. Description max 100 chars.
