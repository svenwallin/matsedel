FROM docker.io/python:3.11-alpine

ARG LITESTREAM_VERSION=0.5.13

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Litestream for continuous SQLite replication to S3
RUN set -eux; \
	apk add --no-cache ca-certificates wget tar; \
	arch="$(apk --print-arch)"; \
	case "$arch" in \
		x86_64) ls_arch="x86_64" ;; \
		aarch64) ls_arch="arm64" ;; \
		*) echo "Unsupported architecture: $arch"; exit 1 ;; \
	esac; \
	wget -O /tmp/litestream.tar.gz "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-${ls_arch}.tar.gz"; \
	mkdir -p /tmp/litestream; \
	tar -xzf /tmp/litestream.tar.gz -C /tmp/litestream; \
	mv /tmp/litestream/litestream /usr/local/bin/litestream; \
	chmod +x /usr/local/bin/litestream; \
	rm -rf /tmp/litestream /tmp/litestream.tar.gz

# Copy application files
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY litestream.yml /etc/litestream.yml

# Create data directory for SQLite and uploads with proper permissions
RUN mkdir -p /app/data/uploads && chmod 755 /app/data && chmod 755 /app/data/uploads

RUN chmod +x /app/app/run_with_litestream.sh

WORKDIR /app/app

EXPOSE 5000

CMD ["/app/app/run_with_litestream.sh"]
