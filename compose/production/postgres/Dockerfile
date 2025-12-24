FROM docker.io/postgres:17

# Use faster Debian mirror (CDN)
RUN sed -i 's/deb.debian.org/cloudfront.debian.net/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
