FROM ctfd/ctfd:3.7.0

# Switch to root user to install new packages
USER root

# Install the PostgreSQL driver
RUN pip install psycopg2-binary

# Fix permissions just in case
RUN mkdir -p /var/log/CTFd /var/uploads && chown -R 1001:1001 /var/log/CTFd /var/uploads

# Switch back to the default CTFd user for security
USER 1001

ENTRYPOINT []

# Start Gunicorn directly (Listens on Port 8000)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "1", "--timeout", "200", "CTFd:create_app()"]