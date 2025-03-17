# Use Balena's Python build image for Raspberry Pi 4 (64-bit) to ensure compilation tools
FROM balenalib/raspberrypi4-64-python:3.10-build AS builder

# Install build tools and utilities required for building lg and lgpio
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    swig \
    wget \
    unzip

# Set the working directory for the build
WORKDIR /usr/src/app

# Download, build, and install the native lg library
RUN wget http://abyz.me.uk/lg/lg.zip && \
    unzip lg.zip && \
    \
    # Handle the extracted folder (lg-master or lg)
    if [ -d "lg-master" ]; then mv lg-master lg; elif [ -d "lg" ]; then echo "Folder is named lg"; else echo "Expected lg folder not found"; exit 1; fi && \
    cd lg && \
    make && \
    make install && \
    \
    # Clean up
    cd .. && rm -rf lg lg.zip

# Use the runtime image for the final stage
FROM balenalib/raspberrypi4-64-python:3.10-run

# Copy only the necessary files from the builder stage
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include

# Set the working directory for the app
WORKDIR /usr/src/app

# Copy requirements.txt into the container
COPY requirements.txt requirements.txt

# Install Python dependencies, including lgpio
# Remove --no-binary=lgpio to allow prebuilt wheels if available, falling back to source
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into the container
COPY . ./

# Set environment variable for production (optional)
ENV FLASK_ENV=production

# Run the main application (assuming app.py is at the project root)
CMD ["python", "-u", "app.py"]