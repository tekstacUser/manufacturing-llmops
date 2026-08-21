# Frontend container (predefined chatbot UI - not a student TODO area).
FROM nginx:1.27-alpine

RUN apk add --no-cache curl gettext

COPY static/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# BACKEND_PUBLIC_URL / LANGFUSE_PUBLIC_URL are the browser-facing URLs
# (i.e. http://localhost:<host-port>) - substituted into env.js at
# container start so the static UI knows where to send requests.
ENV BACKEND_PUBLIC_URL=http://localhost:8080
ENV LANGFUSE_PUBLIC_URL=http://localhost:3030

COPY docker-entrypoint.sh /docker-entrypoint.d/40-render-env.sh
RUN chmod +x /docker-entrypoint.d/40-render-env.sh

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:80/healthz || exit 1
