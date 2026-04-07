import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
import ipaddress
from ping3 import ping
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import re
import platform
import socket

load_dotenv()

class TopologyMapper:
    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def get_my_ip(self):
        """Get the local IP address of this machine"""
        try:
            # Create a socket connection to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
            return my_ip
        except:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return None
    
    def get_mac_address(self, ip):
        """Get MAC address for an IP using ARP table"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(f"arp -a {ip}", shell=True, capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if ip in line and 'dynamic' in line:
                        parts = line.split()
                        for part in parts:
                            if re.match(r'([0-9A-Fa-f]{2}[-:]){5}([0-9A-Fa-f]{2})', part):
                                return part.upper()
            else:
                result = subprocess.run(f"arp -n {ip}", shell=True, capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if ip in line:
                        parts = line.split()
                        for part in parts:
                            if re.match(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', part):
                                return part.upper()
        except:
            pass
        return None
    
    def is_virtual_mac(self, mac):
        """Check if MAC address belongs to virtual/container interface"""
        if not mac:
            return True  # No MAC = likely virtual
        
        mac_upper = mac.upper()
        
        virtual_prefixes = [
            '00:15:5D',  # Hyper-V
            '00:0C:29',  # VMware
            '00:50:56',  # VMware
            '00:05:69',  # VMware
            '08:00:27',  # VirtualBox
            '52:54:00',  # KVM/QEMU
            '02:42:',    # Docker
            '00:1C:42',  # Parallels
            '00:03:FF',  # Virtual PC
            '0A:00:27',  # VirtualBox
        ]
        
        for prefix in virtual_prefixes:
            if mac_upper.startswith(prefix):
                return True
        
        # Locally administered addresses (often virtual)
        if len(mac_upper) >= 2 and mac_upper[0:2] in ['02', '06', '0A', '0E', '12', '16', '1A', '1E']:
            return True
        
        return False
    
    def discover_devices(self, network_cidr, max_ips=None, max_workers=20):
        """Discover ONLY REAL devices (filter out virtual/container interfaces)"""
        devices = []
        
        try:
            network = ipaddress.ip_network(network_cidr, strict=False)
            all_hosts = list(network.hosts())
            
            if max_ips:
                all_hosts = all_hosts[:max_ips]
            
            # Get your own IP address
            my_ip = self.get_my_ip()
            if my_ip:
                print(f"🖥️  Your IP: {my_ip}")
            
            print(f"🔍 Scanning {len(all_hosts)} IPs...")
            real_count = 0
            virtual_count = 0
            
            def check_device(ip):
                nonlocal real_count, virtual_count
                ip_str = str(ip)
                try:
                    response_time = ping(ip_str, timeout=0.5)
                    if response_time is not None:
                        # ALWAYS include your own device
                        if ip_str == my_ip:
                            real_count += 1
                            return {
                                "ip": ip_str,
                                "status": "alive",
                                "mac": "Self",
                                "response_ms": round(response_time * 1000, 2)
                            }
                        
                        # For other IPs, check MAC
                        mac = self.get_mac_address(ip_str)
                        
                        # Skip virtual MACs but keep real ones
                        if not self.is_virtual_mac(mac):
                            real_count += 1
                            return {
                                "ip": ip_str,
                                "status": "alive",
                                "mac": mac if mac else "Unknown",
                                "response_ms": round(response_time * 1000, 2)
                            }
                        else:
                            virtual_count += 1
                except:
                    pass
                return None
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(check_device, ip) for ip in all_hosts]
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        devices.append(result)
            
            # Sort devices by IP for consistent display
            devices.sort(key=lambda x: list(map(int, x['ip'].split('.'))))
            
            print(f"📊 Results: {real_count} REAL devices, {virtual_count} virtual/fake devices filtered out")
            print(f"✅ Found devices: {[d['ip'] for d in devices]}")
                        
        except Exception as e:
            return {"error": str(e)}
        
        return devices
    
    def get_ai_insights(self, devices, network_cidr):
        """Get AI-powered insights about network topology"""
        
        if not devices:
            return {
                "insights": "No real devices discovered. Check network range or firewall.",
                "recommendations": "Make sure you're on the correct network and try again."
            }
        
        all_ips = [d['ip'] for d in devices]
        gateway_present = any(ip.endswith('.1') for ip in all_ips)
        
        prompt = f"""
Network Range: {network_cidr}
REAL Devices Found: {len(devices)} devices
Device IPs: {all_ips}
Gateway present: {gateway_present}

Return ONLY valid JSON:
{{"insights": "brief analysis of this small network", "recommendations": "practical suggestions for this setup"}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            clean = response.text.strip()
            if clean.startswith('```json'):
                clean = clean[7:]
            if clean.startswith('```'):
                clean = clean[3:]
            if clean.endswith('```'):
                clean = clean[:-3]
            clean = clean.strip()
            result = json.loads(clean)
            return result
        except Exception as e:
            print(f"AI error: {e}")
            return {
                "insights": f"Found {len(devices)} real devices in {network_cidr}",
                "recommendations": "Document your network devices and monitor for changes."
            }