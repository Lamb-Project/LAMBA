#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for HTTPS development
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import ipaddress
import os

def generate_ssl_certificate():
    """Generate self-signed SSL certificate for development"""
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Define certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Spain"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Barcelona"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LAMBA Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, "100.97.184.20"),
    ])
    
    # Define certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Certificate valid for 1 year
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("*.localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address("100.97.184.20")),  # Your Tailscale IP
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Create SSL directory if it doesn't exist
    ssl_dir = "ssl"
    os.makedirs(ssl_dir, exist_ok=True)
    
    # Write certificate to file
    cert_path = os.path.join(ssl_dir, "cert.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Write private key to file
    key_path = os.path.join(ssl_dir, "key.pem")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print(f"✅ SSL certificate generated successfully!")
    print(f"📁 Certificate: {cert_path}")
    print(f"🔑 Private key: {key_path}")
    print(f"🌐 Valid for: localhost, 127.0.0.1, 100.97.184.20")
    print(f"⏰ Valid until: {cert.not_valid_after}")

if __name__ == "__main__":
    try:
        generate_ssl_certificate()
    except ImportError:
        print("❌ Error: cryptography library not found.")
        print("📦 Install it with: pip install cryptography")
    except Exception as e:
        print(f"❌ Error generating certificate: {e}")

