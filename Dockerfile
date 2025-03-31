# Use Balena's Python runtime image for Raspberry Pi 5 (64-bit)
FROM balenalib/raspberrypi5-debian-python:3.10-run

# Install runtime dependencies (libgpiod2 is optional, kept for compatibility)
RUN apt-get update && apt-get install -y \
    libgpiod2

# Set the working directory for the app
WORKDIR /usr/src/app

# Copy requirements.txt into the container
COPY requirements.txt requirements.txt

# Install Python dependencies, including lgpio
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into the container
COPY . ./

# Set environment variable for production
ENV FLASK_ENV=production

# Run the main application with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]