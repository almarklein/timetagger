#!/usr/bin/env python3
"""
Calculate credentials with SHA256 hash of password.
"""
import hashlib
import getpass

user = input("Username: ")
pw = getpass.getpass()
pwhash = hashlib.sha256(pw.encode()).hexdigest()
print(f"\nCredentials to put in env:\n  {user}:{pwhash}")
