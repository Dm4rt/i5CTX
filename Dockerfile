FROM ctfd/ctfd:3.7.0

USER root
RUN pip install psycopg2-binary
RUN mkdir -p /var/log/CTFd /var/uploads && chown -R 1001:1001 /var/log/CTFd /var/uploads

USER 1001

# Bypass strict entrypoint
ENTRYPOINT []

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "1", "-k", "gthread", "--threads", "4", "--timeout", "200", "--no-sendfile", "CTFd:create_app()"]