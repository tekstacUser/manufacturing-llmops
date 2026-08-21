# qwen-1.5b

Place the pre-provisioned GGUF file here before starting the stack:

```
qwen2.5-1.5b-instruct-fp16.gguf
```

This directory is mounted read-only into the `bentoml-medium` container at
`/models/qwen-1.5b`. No download happens automatically - the assessment
environment provisions this file ahead of time.
