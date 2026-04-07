# 🗺️ AI-Powered Network Topology Mapper

An intelligent network discovery tool that scans live devices on your local network using ICMP ping sweeps, filters out virtual interfaces, and provides AI-powered topology analysis and visualization.

---

## 🎯 What It Does

Scan your network (192.168.1.0/24) → AI instantly tells you:

- **DEVICES FOUND:** How many live devices are active
- **DENSITY PATTERNS:** IP utilization and distribution gaps
- **GATEWAY STATUS:** Whether router (.1) is present
- **RECOMMENDATIONS:** VLAN segmentation, DHCP optimization, IPAM implementation

Works on any local network you're connected to.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python + Flask |
| **AI Engine** | Google Gemini 2.5 Flash |
| **Visualization** | Plotly + NetworkX |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Network Discovery** | ICMP Ping, ARP Tables, MAC Filtering |

---

## 📊 Features

| Feature | Description |
|---------|-------------|
| **Real-Time Scanning** | Discovers live devices in seconds using parallel threading |
| **Virtual Interface Filtering** | Filters out Docker, VMware, VirtualBox, Hyper-V false positives |
| **AI-Powered Insights** | Analyzes network density, distribution, gateway status |
| **Interactive Topology Map** | Color-coded graph (red = gateway, green = devices) |
| **PNG Export** | One-click export of topology diagram |
| **Dark Theme Dashboard** | Professional, modern UI |

---

## 🎥 Demo

[Demo Video](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

---

## 🎓 What This Demonstrates

✅ AI integration into real applications  
✅ Network discovery (ICMP, ARP, MAC filtering)  
✅ Full-stack development (Flask + modern frontend)  
✅ Data visualization (Plotly + NetworkX)  
✅ Professional UI design for customer-facing tools
