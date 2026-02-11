"""
Simple password hasher using bcrypt directly
"""
import bcrypt

# Your password
password = "admin123"

# Generate hash
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"Hashed password: {hashed.decode()}")
print("\nCopy this hash to your secrets.toml file")
