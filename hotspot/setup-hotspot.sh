#!/bin/bash

# Identify the USB WiFi dongle (assumes it's not the onboard WiFi)
WIFI_DEVICE=$(iw dev | grep -A 1 "Interface" | grep -v "Interface" | awk '{print $1}' | grep -v "wlan0" | head -n 1)
if [ -z "$WIFI_DEVICE" ]; then
    echo "No USB WiFi dongle detected. Exiting."
    exit 1
fi

# Stop any existing hostapd and dnsmasq instances
systemctl stop hostapd
systemctl stop dnsmasq

# Configure the WiFi interface as an access point
ip link set $WIFI_DEVICE down
ip addr add 192.168.4.1/24 dev $WIFI_DEVICE
ip link set $WIFI_DEVICE up

# Configure DHCP and DNS (using dnsmasq)
echo "interface=$WIFI_DEVICE" > /etc/dnsmasq.conf
echo "dhcp-range=192.168.4.2,192.168.4.100,12h" >> /etc/dnsmasq.conf
echo "address=/localhost/192.168.4.1" >> /etc/dnsmasq.conf  # Redirect localhost to AP IP

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

# Start services
systemctl start dnsmasq
systemctl start hostapd

echo "Hotspot 'Humisense' started on $WIFI_DEVICE with password 123456789"