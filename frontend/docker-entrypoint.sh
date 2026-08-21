#!/bin/sh
# Runs automatically via the base nginx image's /docker-entrypoint.d/ hook
# mechanism before nginx starts. Renders env.js from the template using the
# container's environment variables so the static frontend knows the
# browser-facing (host) URLs for the backend API and Langfuse.
set -e

envsubst '${BACKEND_PUBLIC_URL} ${LANGFUSE_PUBLIC_URL}' \
  < /usr/share/nginx/html/env.js.template \
  > /usr/share/nginx/html/env.js

echo "Rendered env.js:"
cat /usr/share/nginx/html/env.js
