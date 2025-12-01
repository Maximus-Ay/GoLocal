import bcrypt
import grpc
import time
import os
import threading
from concurrent import futures
from typing import Dict, Any

# Import the newly modified simulation core components
from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode, User 

# The following imports are from your uploaded files:
import cloudsecurity_pb2
import cloudsecurity_pb2_grpc
from utils import send_otp 

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

# A lock to ensure only one thread modifies the simulation state (NETWORK) at a time
SIMULATION_LOCK = threading.Lock()

def load_users_from_credentials(file_path='credentials'):
    """Loads users from the credentials file and adds them to the simulation network."""
    users_loaded = 0
    # Set default quota to 2GB as requested
    TWO_GB_BYTES = 2 * 1024 * 1024 * 1024 
    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 3:
                    username, _, _ = parts
                    # Use 2GB as the default quota for all authenticated users
                    user = User(user_id=username, name=username, total_quota=TWO_GB_BYTES) 
                    NETWORK.add_user(user)
                    users_loaded += 1
        print(f"Loaded {users_loaded} users with a 2GB quota into the simulation network.")
    except FileNotFoundError:
        print(f"Error: Credentials file '{file_path}' not found. Cannot load users.")
    except Exception as e:
        print(f"Error loading credentials for simulation: {e}")

load_users_from_credentials()
# -------------------------------

# --- gRPC Service Implementation ---
class UserServiceSkeleton(cloudsecurity_pb2_grpc.UserServiceServicer):
    
    AUTHENTICATED_USERS: Dict[str, str] = {} 
    
    def login(self, request, context) -> cloudsecurity_pb2.Response:
        """Handles user login authentication."""
        result = self.checkId(request.login, request.password)
        
        if "OTP" in result:
            # If login successful, establish session
            self.AUTHENTICATED_USERS[request.login] = request.login 
            print(f"SERVER LOG: User '{request.login}' authenticated and session started.")
            
        return cloudsecurity_pb2.Response(result=result)

    def checkId(self, login, pwd) -> str:
        """Authenticates user against the credentials file."""
        credentials = {}
        emails = {}
        file_path = 'credentials' 
        
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    username, email, password = line.strip().split(',')
                    credentials[username] = password
                    emails[username] = email
        except FileNotFoundError:
            return "Error: Credentials file not found on server."
        
        hashed_password = credentials.get(login)
        if (hashed_password and 
            bcrypt.checkpw(pwd.encode('utf-8'), hashed_password.encode('utf-8'))):
            
            # Successful authentication: send OTP and return message
            return send_otp(emails[login])
        else:
            return "Unauthorized"
    
    def get_status(self, request, context) -> cloudsecurity_pb2.Response:
        """Returns the user's current quota and simulation status."""
        user_id = request.login
        
        if user_id not in self.AUTHENTICATED_USERS:
            return cloudsecurity_pb2.Response(result="Error: Not authenticated. Please login first.")

        # Use the lock when reading the global NETWORK object
        with SIMULATION_LOCK:
            user = NETWORK.get_user_quota_info(user_id)
            stats = NETWORK.get_network_stats()
            
            if not user:
                 return cloudsecurity_pb2.Response(result="Error: User not found in network.")
    
            # Format the status report
            status_report = (
                f"--- Cloud Storage Status ---\n"
                f"User: {user.name}\n"
                f"Quota Used: {user.used_quota / 1024**2:.2f}MB / {user.total_quota / 1024**2:.2f}MB\n"
                f"Virtual Time: {stats['simulation_time_seconds']:.4f}s\n"
                f"Active Transfers: {stats['active_transfers']}\n"
                f"Node2 Storage Util: {node2.get_storage_utilization()['utilization_percent']:.4f}%\n"
                f"----------------------------"
            )
            return cloudsecurity_pb2.Response(result=status_report)

    def upload_file(self, request, context) -> cloudsecurity_pb2.Response:
        """Handles file upload initiation and simulation."""
        user_id = request.login
        file_name = request.file_name
        file_size_bytes = request.file_size
        
        if user_id not in self.AUTHENTICATED_USERS:
            return cloudsecurity_pb2.Response(result="Error: Not authenticated. Please login first.")

        # CRITICAL: Use the lock for any operation that changes the simulation state
        with SIMULATION_LOCK:
            # 1. Initiate transfer (handles user quota check and node capacity check)
            transfer = NETWORK.initiate_file_transfer(
                source_node_id=DEFAULT_SOURCE_NODE_ID,
                target_node_id=DEFAULT_TARGET_NODE_ID,
                file_name=file_name,
                file_size=file_size_bytes,
                user_id=user_id
            )

            if not transfer:
                # The NETWORK.initiate_file_transfer prints the specific error (Quota/Storage Full)
                user = NETWORK.get_user_quota_info(user_id)
                if user.used_quota + file_size_bytes > user.total_quota:
                     error_message = f"❌ Upload failed: User quota exceeded."
                else:
                     error_message = f"❌ Upload failed: Target node ({DEFAULT_TARGET_NODE_ID}) storage full."

                return cloudsecurity_pb2.Response(result=error_message)


            # 2. Simulate the transfer to completion (D.E.S. Loop)
            upload_log = [f"Initiated Transfer ID: {transfer.file_id}"]
            total_chunks = len(transfer.chunks)
            
            while True:
                chunks_done, completed = NETWORK.process_file_transfer(
                    source_node_id=DEFAULT_SOURCE_NODE_ID,
                    target_node_id=DEFAULT_TARGET_NODE_ID,
                    file_id=transfer.file_id,
                    chunks_per_step=10 # Process 10 chunks per step for speed
                )

                if completed:
                    break
                
            # 3. Finalization
            user = NETWORK.get_user_quota_info(user_id)
            quota_used = user.used_quota / 1024**2 if user else 0
            quota_total = user.total_quota / 1024**2 if user else 0
            
            status_summary = (
                f"\n✅ Upload COMPLETE: {file_name}\n"
                f"  Total Chunks: {total_chunks}\n"
                f"  New Virtual Time: {NETWORK.simulation_time:.4f}s\n"
                f"  User Quota: {quota_used:.2f}MB / {quota_total:.2f}MB\n"
            )
            return cloudsecurity_pb2.Response(result="\n".join(upload_log) + status_summary)


def run():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cloudsecurity_pb2_grpc.add_UserServiceServicer_to_server(UserServiceSkeleton(), server)
    server.add_insecure_port('[::]:51234')
    print('Starting Cloud Server on port 51234. Waiting for clients...')
    server.start()
    try:
        while True:
            time.sleep(10) # Keep the server running
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    run()