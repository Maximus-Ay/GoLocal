from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode, User 

# --- Helper Function for Clean Output ---
def print_stats(network: StorageVirtualNetwork, node2: StorageVirtualNode):
    """Prints key simulation and utilization metrics."""
    stats = network.get_network_stats()
    
    print("\n--- Network Status ---")
    print(f"Simulation Time: {stats['simulation_time_seconds']:.4f} seconds (Virtual Time)")
    print(f"Active Transfers: {stats['active_transfers']}")
    print(f"Network Utilization: {stats['bandwidth_utilization']:.2f}%")
    
    # Report User Quota
    user_max = network.users.get("user_max")
    if user_max:
        print(f"User Quota (Maximus): {user_max.used_quota / 1024**2:.2f}MB / {user_max.total_quota / 1024**2:.2f}MB")
        
    storage_util = node2.get_storage_utilization()
    print(f"Storage utilization on node2: {storage_util['utilization_percent']:.4f}%")
    print("----------------------\n")
# ----------------------------------------

# Create network
network = StorageVirtualNetwork()

# --- User Setup: Define Quotas ---
# User with a generous quota (200MB)
user_max = User("user_max", "Maximus A.", total_quota=200 * 1024 * 1024) 
# User with a very small quota (50MB) to demonstrate failure
user_guest = User("user_guest", "Guest U.", total_quota=50 * 1024 * 1024) 

network.add_user(user_max)
network.add_user(user_guest)
# ---------------------------------

# Create nodes
node1 = StorageVirtualNode("node1", cpu_capacity=4, memory_capacity=16, storage_capacity=500, bandwidth=1000)
node2 = StorageVirtualNode("node2", cpu_capacity=8, memory_capacity=32, storage_capacity=1000, bandwidth=2000)

# Add nodes to network
network.add_node(node1)
network.add_node(node2)

# Connect nodes with 1Gbps link
network.connect_nodes("node1", "node2", bandwidth=1000)

# --- SCENARIO 1: Successful Transfer within Quota (Maximus uploads 100MB) ---
print("\n--- SCENARIO 1: Successful 100MB Upload (user_max) ---")
file_size_bytes_100m = 100 * 1024 * 1024  # 100MB
transfer1 = network.initiate_file_transfer(
    source_node_id="node1",
    target_node_id="node2",
    file_name="project_files.zip",
    file_size=file_size_bytes_100m,
    user_id="user_max" 
)

if transfer1:
    print(f"Transfer initiated: {transfer1.file_id}")
    step_count = 0
    # Process transfer until complete
    while True:
        step_count += 1
        chunks_done, completed = network.process_file_transfer(
            source_node_id="node1",
            target_node_id="node2",
            file_id=transfer1.file_id,
            chunks_per_step=3 
        )
        
        if completed:
            print(f"✅ Transfer 1 completed successfully! Total Virtual Time: {network.simulation_time:.4f} seconds")
            print_stats(network, node2)
            break
            
# --- SCENARIO 2: Quota Failure (Guest tries to upload 100MB against a 50MB quota) ---
print("\n--- SCENARIO 2: Quota Failure (user_guest uploads 100MB) ---")
file_size_bytes_100m = 100 * 1024 * 1024  # 100MB
transfer2 = network.initiate_file_transfer(
    source_node_id="node1",
    target_node_id="node2",
    file_name="oversized_file.dat",
    file_size=file_size_bytes_100m,
    user_id="user_guest" 
)

if not transfer2:
    print("✅ Quota Check Success: Transfer failed to initiate due to quota rules.")
    print(f"Guest Quota Used: {network.users['user_guest'].used_quota / 1024**2:.2f}MB / {network.users['user_guest'].total_quota / 1024**2:.2f}MB")
    print_stats(network, node2)