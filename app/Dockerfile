FROM python:3.11

EXPOSE 8080
WORKDIR /app

# Copy everything into the container
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Install Cloud SQL Auth Proxy
ADD https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 /cloud_sql_proxy
RUN chmod +x /cloud_sql_proxy

# Add and set permissions for the startup script
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

# Run the startup script
ENTRYPOINT ["/startup.sh"]

