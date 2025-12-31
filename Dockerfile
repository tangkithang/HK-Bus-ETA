FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy application code
COPY server.py analyze_route.py ./

# Copy only the necessary data subfolder to keep image size valid
# We need to recreate the directory structure analyze_route.py expects
RUN mkdir -p hk-bus-time-between-stops-pages/times_hourly
COPY hk-bus-time-between-stops-pages/times_hourly ./hk-bus-time-between-stops-pages/times_hourly

# Set environment variable for Python buffering
ENV PYTHONUNBUFFERED=1

# Command to run the application
# Cloud Run injects PORT environment variable
CMD ["python", "server.py"]
