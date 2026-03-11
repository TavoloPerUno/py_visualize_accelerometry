# Dockerfile for deploying the Panel demo app on Hugging Face Spaces.
#
# Hugging Face Spaces (Docker SDK) exposes port 7860 by default.
# The app runs with basic-auth using demo credentials.

FROM python:3.12-slim

# Avoid interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . /app

# Generate synthetic demo data
RUN python scripts/generate_demo_data.py

# Hugging Face Spaces expects port 7860
EXPOSE 7860

CMD ["panel", "serve", "/app/demo/app_demo.py", \
     "--address", "0.0.0.0", \
     "--port", "7860", \
     "--basic-auth", "/app/demo/credentials.json", \
     "--cookie-secret", "demo-cookie-secret-not-for-production", \
     "--allow-websocket-origin", "*", \
     "--basic-login-template", "/app/visualize_accelerometry/templates/login.html", \
     "--num-procs", "1"]
