# Nic's 5 Nips on the apps box. Runs serve.py (basic auth + the open-house
# window) rather than plain nginx, so the wedding-day unlock logic is the same
# code that ran on the Mac. Replaces the old nginx/.htpasswd image, 24 Sep 2026.
FROM python:3.12-alpine
WORKDIR /app
COPY serve.py /app/serve.py
COPY public/ /app/public/
ENV NICKS_PORT=8104 BIND=0.0.0.0
EXPOSE 8104
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- --header="Authorization: Basic aWFpbjppYWluczVuaXBz" http://127.0.0.1:8104/ >/dev/null || exit 1
CMD ["python", "-u", "serve.py"]
