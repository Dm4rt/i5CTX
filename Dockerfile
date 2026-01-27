FROM ctfd/ctfd:3.7.0

# Switch to root user to install new packages
USER root

# Install the PostgreSQL driver
RUN pip install psycopg2-binary

# Switch back to the default CTFd user for security
USER 1001