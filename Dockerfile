FROM ctfd/ctfd:3.7.0

USER root
# 1. Install DB driver AND gevent (High performance, Low Memory)
RUN pip install psycopg2-binary gevent

# 2. Fix permissions just in case
RUN mkdir -p /var/log/CTFd /var/uploads && chown -R 1001:1001 /var/log/CTFd /var/uploads

USER 1001

# 3. Bypass strict entrypoint
ENTRYPOINT []

# 4. Run with GEVENT (The secret to running on free tier)
# -k gevent: Uses "Greenlets" instead of Threads (Saves ~100MB RAM)
# --worker-connections 1000: Handles many users at once
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "1", "-k", "gevent", "--worker-connections", "1000", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "CTFd:create_app()"]