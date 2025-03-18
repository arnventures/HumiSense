# Use Balena's Python build image for Raspberry Pi 5 (64-bit) to ensure compilation tools
FROM balenalib/raspberrypi5-debian-python:3.10-build AS builder

# Install build tools and utilities required for building lg and lgpio
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    swig \
    wget \
    unzip \
    libgpiod-dev

# Set the working directory for the build
WORKDIR /usr/src/app

# Download, build, and install the native lg library
RUN wget http://abyz.me.uk/lg/lg.zip && \
    unzip lg.zip && \
    # Handle the extracted folder (lg-master or lg)
    if [ -d "lg-master" ]; then mv lg-master lg; elif [ -d "lg" ]; then echo "Folder is named lg"; else echo "Expected lg folder not found"; exit 1; fi && \
    cd lg && \
    make && \
    make install && \
    # Clean up
    cd .. && rm -rf lg lg.zip

# Use the runtime image for the final stage
FROM balenalib/raspberrypi5-debian-python:3.10-run

# Install runtime dependencies, including libgpiod
RUN apt-get update && apt-get install -y \
    libgpiod2

# Copy the lg library and headers from the builder stage
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include

# Update the dynamic linker run-time bindings and verify library
RUN ldconfig && ls /usr/local/lib/liblgpio.so.1

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