import bcrypt
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Ensure we import the correct variables for login
from params import from_email, app_password 

def hash_password(password: str) -> str:
    """Hashes the plain text password using bcrypt."""
    # bcrypt.gensalt() generates a salt, and hashpw performs the hashing.
    return bcrypt.hashpw(password.encode('utf-8'), 
                         bcrypt.gensalt()).decode('utf-8')

def generate_otp() -> str:
    """Generates a random 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp(to_email: str) -> str:
    """
    Sends an OTP code via email using the configured SMTP server.
    
    Returns the generated OTP code (str) on success, allowing the 
    server to cache it for verification.
    """
    otp = generate_otp()

    # Sender configuration
    subject = "Your OTP Code for the cloud security simulator"
    body = f"Your OTP code is: {otp}"

    # Create the email
    msg = MIMEMultipart()
    # Use the variable here for consistency
    msg['From'] = from_email 
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect and send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            print(f"Starting tls session on smtp.gmail.com:587 .........", end='')
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            print('[OK]')
            print(f"login to the server with {from_email} .........", end='')
            
            # Use variables from params.py for login
            server.login(from_email, app_password)
            
            print('[OK]')
            print(f"Sending OTP data to {to_email}  .........", end='')
            server.send_message(msg)
            print('[OK]')
            
            # --- CRITICAL: Return the OTP code itself ---
            print(f"OTP data sent to {to_email} successfully!")
            return otp # Return the generated OTP for the server to cache

    except Exception as e:
        print(f"\n[ERROR] Failed to send email to {to_email}. Ensure 'params.py' has correct app_password and email is valid.")
        print(f"SMTP Error Details: {e}")
        # Raising the error to ensure the gRPC server logs it or returns a failure status
        raise