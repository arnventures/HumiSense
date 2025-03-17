FROM balenalib/raspberrypi5-debian:latest

# Install required packages
RUN apt-get update && apt-get install -y hostapd dnsmasq iproute2 iw procps

# Copy the hotspot script
COPY setup-hotspot.sh /usr/src/app/setup-hotspot.sh
RUN chmod +x /usr/src/app/setup-hotspot.sh

# Run the script on container start
CMD ["/usr/src/app/setup-hotspot.sh"]