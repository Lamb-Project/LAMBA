#!/usr/bin/env python3
"""
HTTPS server launcher for LAMBA application
"""

import uvicorn
import os
import sys
from pathlib import Path

def run_https_server():
    """Run the FastAPI application with HTTPS support"""
    
    # SSL certificate paths
    cert_file = Path("ssl/cert.pem")
    key_file = Path("ssl/key.pem")
    
    # Check if SSL certificates exist
    if not cert_file.exists() or not key_file.exists():
        print("❌ SSL certificates not found!")
        print("🔧 Run 'python generate_ssl_cert.py' to generate them first.")
        sys.exit(1)
    
    # Set HTTPS environment variable
    os.environ["HTTPS_ENABLED"] = "true"
    os.environ["ALLOWED_ORIGINS"] = "https://100.97.184.20:9099,https://localhost:9099"
    
    print("🚀 Starting LAMBA with HTTPS...")
    print(f"📁 Certificate: {cert_file.absolute()}")
    print(f"🔑 Private key: {key_file.absolute()}")
    print("🌐 Available at:")
    print("   - https://100.97.184.20:9099 (Tailscale)")
    print("   - https://localhost:9099 (Local)")
    print("")
    print("⚠️  You may see a security warning in your browser.")
    print("   This is normal for self-signed certificates.")
    print("   Click 'Advanced' and 'Proceed to site' to continue.")
    print("")
    
    # Run server with SSL
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9099,
        ssl_keyfile=str(key_file),
        ssl_certfile=str(cert_file),
        reload=True
    )

if __name__ == "__main__":
    run_https_server()

