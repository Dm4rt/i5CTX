FROM ctfd/ctfd:3.7.0

USER root

# 1. Install DB driver AND gevent
RUN pip install psycopg2-binary gevent

# 2. Copy custom plugins into CTFd
COPY plugins /opt/CTFd/CTFd/plugins

# 3. Fix permissions just in case
RUN mkdir -p /var/log/CTFd /var/uploads && \
    chown -R 1001:1001 /var/log/CTFd /var/uploads /opt/CTFd/CTFd/plugins

USER 1001

# 4. Bypass strict entrypoint
ENTRYPOINT []

# 5. Run with GEVENT
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "1", "-k", "gevent", "--worker-connections", "1000", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "CTFd:create_app()"]