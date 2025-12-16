FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && apt-get clean

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy dependencies (assuming you have requirements.txt)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Copy start script and make executable
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["/bin/bash", "./start.sh"]
