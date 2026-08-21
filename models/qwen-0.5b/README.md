# qwen-0.5b

Place the pre-provisioned GGUF file here before starting the stack:

```
qwen2.5-0.5b-instruct-q4_k_m.gguf
```

This directory is mounted read-only into the `bentoml-small` container at
`/models/qwen-0.5b`. No download happens automatically - the assessment
environment provisions this file ahead of time.
