import sys
import grpc
import cloudsecurity_pb2
import cloudsecurity_pb2_grpc
import os

# --- Constants ---
SERVER_ADDRESS = 'localhost:51234'
# ---

def print_help():
    """Prints usage instructions."""
    # Updated Heading and removed 'Testing' / 'gRPC' references
    print("\n--- GoLocal Virtual Storage Client ---\n")
    print("Commands:")
    # Signup is now the primary command
    print("  python client.py signup <username> <email> <password>     # Register a new account")
    print("  python client.py verify_otp <username> <otp_code>         # Complete registration or log in") 
    print("  python client.py login <username> <password>              # Send OTP to email for existing user")
    print("  python client.py status <username>                        # Check storage quota and virtual network status")
    print("  python client.py upload <username> <file_name> <file_size_MB> # Initiate a file transfer")
    print("\nExamples:")
    print("  python client.py signup newuser test@example.com mysecurepass")
    print("  python client.py verify_otp newuser 123456")
    print("  python client.py status newuser")
    print("  python client.py upload newuser video.mp4 100.2")
    print("----------------------------------------\n")

def run():
    # If no arguments are provided, show help.
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()
    response = None

    # Argument validation based on command
    if command == "signup":
        if len(sys.argv) < 5:
            print("Error: Signup requires <username>, <email>, and <password>.")
            print_help()
            sys.exit(1)
        login = sys.argv[2]
    elif command == "login":
        if len(sys.argv) < 4:
            print("Error: Login requires <username> and <password>.")
            print_help()
            sys.exit(1)
        login = sys.argv[2]
    elif command == "verify_otp" or command == "status":
        if len(sys.argv) < 3:
            print(f"Error: '{command}' requires <username>.")
            print_help()
            sys.exit(1)
        login = sys.argv[2]
    elif command == "upload":
        if len(sys.argv) < 5:
            print("Error: Upload requires <username>, <file_name>, and <file_size_MB>.")
            print_help()
            sys.exit(1)
        login = sys.argv[2]
    else:
        print(f"Error: Unknown command '{command}'.")
        print_help()
        sys.exit(1)
        
    try:
        # Connect to the server
        with grpc.insecure_channel(SERVER_ADDRESS) as channel:
            stub = cloudsecurity_pb2_grpc.UserServiceStub(channel)

            if command == "signup":
                # Get required arguments
                email = sys.argv[3]
                password = sys.argv[4]
                
                print(f"Attempting to register new user '{login}'...")

                response = stub.signup(cloudsecurity_pb2.SignupRequest(
                    login=login,
                    email=email,
                    password=password
                ))
            
            elif command == "login":
                # Get required arguments
                password = sys.argv[3]
                
                print(f"Attempting to log in user '{login}'. A one-time code will be sent to your registered email...")
                
                # The login RPC expects login and password fields.
                response = stub.login(cloudsecurity_pb2.Request(
                    login=login,
                    password=password
                ))

            elif command == "verify_otp":
                # Get required arguments
                otp_code = sys.argv[3]
                
                print(f"Verifying one-time code for user '{login}'...")

                # The verify_otp RPC expects login and otp fields.
                response = stub.verify_otp(cloudsecurity_pb2.VerificationRequest(
                    login=login,
                    otp=otp_code
                ))

            elif command == "status":
                print(f"Requesting storage status for user '{login}'...")
                
                # The get_status RPC expects only the login field.
                response = stub.get_status(cloudsecurity_pb2.Request(
                    login=login
                ))
                
            elif command == "upload":
                # Get required arguments
                file_name = sys.argv[3]
                file_size_mb = sys.argv[4]
                
                try:
                    # Convert MB to bytes
                    file_size_bytes = int(float(file_size_mb) * 1024 * 1024)
                except ValueError:
                    print("Error: <file_size_MB> must be a number (e.g., 50 or 50.5).")
                    sys.exit(1)

                print(f"Initiating upload for user '{login}': {file_name} ({file_size_mb}MB)...\n")
                
                # The upload RPC expects file_name and file_size fields.
                response = stub.upload_file(cloudsecurity_pb2.Request(
                    login=login,
                    file_name=file_name,
                    file_size=file_size_bytes
                ))
                
            if response:
                print("\n--- Server Response ---")
                # Special handling for session token on successful verification
                if command in ["verify_otp"] and response.session_token:
                    print(f"Result: {response.result}")
                    print(f"Session Token: {response.session_token}")
                else:
                    print(f"{response.result}")
                print("-----------------------\n")

    except grpc.RpcError as e:
        print(f"\n--- Connection Error ---")
        print(f"Failed to connect to the GoLocal service. Is the server running?")
        print(f"Status Code: {e.code().name}")
        print(f"Details: {e.details()}")
        print("------------------------\n")
    except Exception as e:
        print(f"\n--- Client Error ---")
        print(f"An unexpected error occurred: {str(e)}")
        print("---------------------\n")

if __name__ == '__main__':
    run()