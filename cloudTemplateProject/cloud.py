import bcrypt
import grpc
import time
import os
import threading
import random 
import string
from concurrent import futures
from typing import Dict, Any, Optional

# Import the newly modified simulation core components
from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode, User 

# The following imports are from your uploaded files:
import cloudsecurity_pb2
import cloudsecurity_pb2_grpc
from utils import send_otp, hash_password # Import hash_password now too!

# --- GLOBAL SIMULATION SETUP ---
# Initialize the Simulation Network and Nodes
NETWORK = StorageVirtualNetwork()
# Node configurations (Node1: 1Gbps, Node2: 2Gbps)
node1 = StorageVirtualNode("node1", cpu_capacity=4, memory_capacity=16, storage_capacity=500, bandwidth=1000)
node2 = StorageVirtualNode("node2", cpu_capacity=8, memory_capacity=32, storage_capacity=1000, bandwidth=2000)
NETWORK.add_node(node1)
NETWORK.add_node(node2)
NETWORK.connect_nodes("node1", "node2", bandwidth=1000)

# Constants
DEFAULT_SOURCE_NODE_ID = "node1"
DEFAULT_TARGET_NODE_ID = "node2"
DEFAULT_QUOTA_BYTES = 2 * 1024**3 # 2GB Default Quota

# A lock to ensure only one thread modifies the simulation state (NETWORK) at a time
SIMULATION_LOCK = threading.Lock()

# --- User Data & OTP Cache ---
# Stores user credentials and profile information
USERS_DB: Dict[str, Dict[str, str]] = {}
# Stores OTP for validation: {username: otp}
OTP_CACHE: Dict[str, str] = {}
# Stores active sessions: {username: session_token}
SESSION_TOKENS: Dict[str, str] = {}

def generate_session_token(length=32) -> str:
    """Generates a random alphanumeric session token."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def load_users_from_credentials(file_path='credentials.txt'):
    """Loads initial users from a file and initializes their network quotas."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    username, email, hashed_password = line.strip().split(',')
                    USERS_DB[username] = {
                        'email': email,
                        'password': hashed_password, # Stored as the bcrypt hash
                    }
                    # Initialize user in the network simulation with a default quota
                    if username not in NETWORK.users:
                        new_user = User(
                            user_id=username, 
                            name=username, 
                            total_quota=DEFAULT_QUOTA_BYTES
                        )
                        NETWORK.add_user(new_user)
                    print(f"Loaded user: {username}")
                except ValueError:
                    print(f"Skipping malformed line in credentials.txt: {line.strip()}")
    else:
        print(f"Warning: credentials.txt not found. Starting with empty user database.")
        
load_users_from_credentials()

# --- gRPC Service Implementation ---

class UserServiceSkeleton(cloudsecurity_pb2_grpc.UserServiceServicer):
    
    # NEW: Handle user registration
    def signup(self, request, context):
        username = request.login
        email = request.email
        password = request.password

        if username in USERS_DB:
            return cloudsecurity_pb2.Response(result=f"Error: User '{username}' already exists.")

        try:
            hashed_password = hash_password(password)
            USERS_DB[username] = {
                'email': email,
                'password': hashed_password,
            }
            # Add user to the virtual network
            new_user = User(
                user_id=username, 
                name=username, 
                total_quota=DEFAULT_QUOTA_BYTES
            )
            NETWORK.add_user(new_user)

            # Send OTP for initial verification/login
            otp = send_otp(email)
            OTP_CACHE[username] = otp
            
            # Save the new user to credentials.txt immediately
            with open('credentials.txt', 'a') as f:
                f.write(f"\n{username},{email},{hashed_password}")

            return cloudsecurity_pb2.Response(
                result=f"User '{username}' created successfully. OTP sent to {email}. Please use 'verify_otp' to continue."
            )
        except Exception as e:
            return cloudsecurity_pb2.Response(
                result=f"Error during signup/OTP send: {str(e)}"
            )

    def login(self, request, context):
        username = request.login
        password = request.password

        if username not in USERS_DB:
            return cloudsecurity_pb2.Response(result="Error: Invalid username or password.")
        
        user_info = USERS_DB[username]

        if not bcrypt.checkpw(password.encode('utf-8'), user_info['password'].encode('utf-8')):
            return cloudsecurity_pb2.Response(result="Error: Invalid username or password.")

        try:
            # Send OTP
            otp = send_otp(user_info['email'])
            OTP_CACHE[username] = otp
            return cloudsecurity_pb2.Response(
                result=f"Login successful. OTP sent to {user_info['email']}. Please use 'verify_otp' to complete login."
            )
        except Exception as e:
            return cloudsecurity_pb2.Response(
                result=f"Error during OTP send: {str(e)}"
            )

    def verify_otp(self, request, context):
        username = request.login
        otp_code = request.otp

        if username not in OTP_CACHE:
            return cloudsecurity_pb2.Response(result="Error: No pending OTP verification for this user.")

        if OTP_CACHE[username] == otp_code:
            # Generate and cache a session token
            session_token = generate_session_token()
            SESSION_TOKENS[username] = session_token
            # Clear OTP as it's been used
            del OTP_CACHE[username]

            return cloudsecurity_pb2.Response(
                result="OTP verified. Session created successfully.",
                session_token=session_token # Return the token to the client
            )
        else:
            return cloudsecurity_pb2.Response(result="Error: Invalid OTP.")

    def get_status(self, request, context):
        username = request.login
        
        user = NETWORK.get_user_quota_info(username)
        if not user:
             return cloudsecurity_pb2.Response(result=f"Error: User '{username}' not found in network registry.")

        quota_used = user.used_quota / 1024**2
        quota_total = user.total_quota / 1024**2
        
        # Get overall network stats
        network_stats = NETWORK.get_network_stats()
        
        result_message = (
            f"--- User Status: {username} ---\n"
            f"Quota Used: {quota_used:.2f} MB / {quota_total:.2f} MB\n"
            f"Quota Remaining: {(quota_total - quota_used):.2f} MB\n\n"
            f"--- Virtual Network Status ---\n"
            f"Simulation Time: {network_stats['simulation_time_seconds']:.4f}s\n"
            f"Active Transfers: {network_stats['active_transfers']}\n"
            f"Network Utilization: {network_stats['bandwidth_utilization']:.2f}%\n"
            f"Storage Utilization (Total): {network_stats['storage_utilization']:.2f}%\n"
        )
        return cloudsecurity_pb2.Response(result=result_message)

    def upload_file(self, request, context):
        user_id = request.login
        file_name = request.file_name
        file_size_bytes = request.file_size
        
        upload_log = [f"Starting virtual upload for {file_name} ({file_size_bytes/1024**2:.2f}MB) by user {user_id}..."]

        user = NETWORK.get_user_quota_info(user_id)
        if not user:
            return cloudsecurity_pb2.Response(result=f"Error: User '{user_id}' not found.")
        
        # 1. Quota Check
        if user.used_quota + file_size_bytes > user.total_quota:
            quota_used_mb = user.used_quota / 1024**2
            quota_total_mb = user.total_quota / 1024**2
            error_msg = (
                f"Error: Quota exceeded. File size ({file_size_bytes/1024**2:.2f}MB) "
                f"would exceed your current quota ({quota_used_mb:.2f}MB/{quota_total_mb:.2f}MB)."
            )
            upload_log.append(error_msg)
            return cloudsecurity_pb2.Response(result="\n".join(upload_log))

        # 2. Initiate Transfer (acquires SIMULATION_LOCK inside)
        try:
            with SIMULATION_LOCK:
                # The virtual file transfer initiation automatically checks storage capacity 
                # and reserves the space and quota if successful.
                transfer = NETWORK.initiate_file_transfer(
                    source_node_id=DEFAULT_SOURCE_NODE_ID,
                    target_node_id=DEFAULT_TARGET_NODE_ID,
                    file_name=file_name,
                    file_size=file_size_bytes,
                    user_id=user_id 
                )
            
        except RuntimeError as e:
            # Handle simulation errors (e.g., storage full, node not found)
            upload_log.append(f"Simulation Error during initiation: {str(e)}")
            return cloudsecurity_pb2.Response(result="\n".join(upload_log))

        if not transfer:
            upload_log.append("Error: Transfer initiation failed (details logged on server).")
            return cloudsecurity_pb2.Response(result="\n".join(upload_log))

        upload_log.append(f"Transfer ID: {transfer.file_id}")
        
        # Get initial time for speed calculation
        initial_time = NETWORK.simulation_time
        
        # 3. Simulate Transfer Progress until completion
        total_chunks = len(transfer.chunks)
        
        while True:
            # The client blocks while the server simulates the transfer step-by-step
            # This is the core of the virtual time progression
            with SIMULATION_LOCK:
                chunks_done, completed = NETWORK.process_file_transfer(
                    source_node_id=DEFAULT_SOURCE_NODE_ID,
                    target_node_id=DEFAULT_TARGET_NODE_ID,
                    file_id=transfer.file_id,
                    chunks_per_step=10 # Process 10 chunks per step for speed
                )

                if completed:
                    break
            
            # This print is useful for seeing the progress on the server side
            # print(f"Progress for {transfer.file_id}: {chunks_done}/{total_chunks} chunks.")
            
        # 4. Finalization and Reporting
        total_time_end = NETWORK.simulation_time
        time_elapsed = total_time_end - initial_time
        # Convert to Mbps: (Bytes * 8) / (Time * 1024 * 1024)
        simulated_speed_mbps = (file_size_bytes * 8) / (time_elapsed * 1024 * 1024) if time_elapsed > 0 else 0
        
        user_after_upload = NETWORK.get_user_quota_info(user_id)
        quota_used = user_after_upload.used_quota / 1024**2 if user_after_upload else 0
        quota_total = user_after_upload.total_quota / 1024**2 if user_after_upload else 0
        
        status_summary = (
            f"\n✅ Upload COMPLETE: {file_name}\n"
            f"  Total Size: {file_size_bytes / 1024**2:.2f} MB\n"
            f"  Virtual Time Taken: {time_elapsed:.4f}s\n"
            f"  Simulated Speed: {simulated_speed_mbps:.2f} Mbps\n"
            f"  New Virtual Time: {total_time_end:.4f}s\n"
            f"  User Quota: {quota_used:.2f}MB / {quota_total:.2f}MB\n"
        )
        return cloudsecurity_pb2.Response(result="\n".join(upload_log) + status_summary)


def run():
    # Set up the gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cloudsecurity_pb2_grpc.add_UserServiceServicer_to_server(UserServiceSkeleton(), server)
    
    # --- FIX HERE: Change binding address to '0.0.0.0:51234' for better compatibility ---
    # Binding to '0.0.0.0' explicitly uses IPv4 and is often more reliable than '[::]'
    server.add_insecure_port('0.0.0.0:51234')
    
    server.start()
    print("gRPC GoLocal Virtual Storage Server started on port 51234. Waiting for requests...")
    try:
        while True:
            time.sleep(86400) # Keep the main thread alive for 24 hours
    except KeyboardInterrupt:
        print("Server shutting down...")
        server.stop(0)

if __name__ == '__main__':
    run()