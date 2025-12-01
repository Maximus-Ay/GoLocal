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
    print("\n--- Cloud Client Usage Guide ---")
    print("Commands:")
    print("  python client.py login <username> <password>")
    print("  python client.py status <username>")
    print("  python client.py upload <username> <file_name> <file_size_MB>")
    print("\nExample:")
    print("  python client.py login johndoe password123")
    print("  python client.py status johndoe")
    print("  python client.py upload johndoe my_thesis.pdf 50.5")
    print("--------------------------------\n")

def run():
    if len(sys.argv) < 3:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    with grpc.insecure_channel(SERVER_ADDRESS) as channel:
        stub = cloudsecurity_pb2_grpc.UserServiceStub(channel)
        response = None
        
        # --- LOGIN Command ---
        if command == "login":
            if len(sys.argv) != 4:
                print("Error: 'login' requires <username> and <password>.")
                print_help()
                sys.exit(1)
            
            login = sys.argv[2]
            password = sys.argv[3]
            print(f"Attempting login for user: {login}...")
            response = stub.login(cloudsecurity_pb2.Request(login=login, password=password))
            
        # --- STATUS Command ---
        elif command == "status":
            if len(sys.argv) != 3:
                print("Error: 'status' requires <username>.")
                print_help()
                sys.exit(1)
                
            login = sys.argv[2]
            print(f"Requesting status for user: {login}...")
            # We use the Request message, only setting the login field
            response = stub.get_status(cloudsecurity_pb2.Request(login=login))

        # --- UPLOAD Command ---
        elif command == "upload":
            if len(sys.argv) != 5:
                print("Error: 'upload' requires <username>, <file_name>, and <file_size_MB>.")
                print_help()
                sys.exit(1)
                
            login = sys.argv[2]
            file_name = sys.argv[3]
            file_size_mb = sys.argv[4]
            
            try:
                # Convert size from MB (input) to Bytes (server expects bytes)
                file_size_bytes = int(float(file_size_mb) * 1024 * 1024)
            except ValueError:
                print("Error: <file_size_MB> must be a number (e.g., 50 or 50.5).")
                sys.exit(1)

            print(f"Initiating upload for user '{login}': {file_name} ({file_size_mb}MB)...")
            
            response = stub.upload_file(cloudsecurity_pb2.Request(
                login=login,
                file_name=file_name,
                file_size=file_size_bytes
            ))
            
        else:
            print(f"Error: Unknown command '{command}'.")
            print_help()
            sys.exit(1)
            
        if response:
            print(f"\n--- Server Response ---\n{response.result}\n-----------------------")

if __name__ == '__main__':
    run()