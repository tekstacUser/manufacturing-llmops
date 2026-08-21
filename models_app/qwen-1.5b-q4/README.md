# qwen-1.5b-q4

Place the pre-provisioned quantized GGUF file here before starting the
quantization profile:

```
qwen2.5-1.5b-instruct-q4_k_m.gguf
```

This directory is mounted read-only into the `bentoml-quantized` container at
`/models_app/qwen-1.5b-q4`. Used for Task 5 (Quantized Model) to compare against
`qwen-1.5b` (the non-quantized medium model). No download happens
automatically - the assessment environment provisions this file ahead of
time.
