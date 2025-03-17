#!/bin/bash

# Explicitly set the USB WiFi dongle
WIFI_DEVICE="wlan1"
if ! iw dev | grep -q "Interface $WIFI_DEVICE"; then
    echo "No USB WiFi dongle ($WIFI_DEVICE) detected. Available interfaces: $(iw dev | grep "Interface" -A 1 | grep -v "Interface")" > /tmp/hotspot-error.log
    exit 1
fi
echo "Using WiFi device: $WIFI_DEVICE" > /tmp/hotspot.log

# Stop any existing hostapd and dnsmasq instances
pkill hostapd
pkill dnsmasq
echo "Stopped existing services" >> /tmp/hotspot.log

# Configure the WiFi interface as an access point
ip link set $WIFI_DEVICE down
ip addr flush dev $WIFI_DEVICE  # Clear existing IP addresses
ip addr add 192.168.4.1/24 dev $WIFI_DEVICE
ip link set $WIFI_DEVICE up
echo "Configured IP and brought up $WIFI_DEVICE" >> /tmp/hotspot.log

# Configure DHCP and DNS (using dnsmasq)
echo "interface=$WIFI_DEVICE" > /etc/dnsmasq.conf
echo "dhcp-range=192.168.4.2,192.168.4.100,12h" >> /etc/dnsmasq.conf
echo "address=/localhost/192.168.4.1" >> /etc/dnsmasq.conf
echo "Configured dnsmasq" >> /tmp/hotspot.log

# Configure hostapd
cat > /etc/hostapd/hostapd.conf <<EOF
interface=$WIFI_DEVICE
driver=nl80211
ssid=Humisense
hw_mode=g
channel=6
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=123456789
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
echo "Configured hostapd" >> /tmp/hotspot.log

# Start services
dnsmasq -C /etc/dnsmasq.conf &
hostapd /etc/hostapd/hostapd.conf &
echo "Started dnsmasq and hostapd" >> /tmp/hotspot.log

echo "Hotspot 'Humisense' started on $WIFI_DEVICE with password 123456789"

# Keep the container running
tail -f /dev/null