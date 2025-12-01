from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode
import time

# --- Helper Function for Clean Output ---
def print_stats(network: StorageVirtualNetwork):
    """Prints key simulation and utilization metrics."""
    stats = network.get_network_stats()
    
    print("\n--- Network Status ---")
    print(f"Simulation Time: {stats['simulation_time_seconds']:.4f} seconds (Virtual Time)") # MODIFIED
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"Active Transfers: {stats['active_transfers']}")
    print(f"Network Utilization: {stats['bandwidth_utilization']:.2f}%")
    print(f"Total Storage Utilization: {stats['storage_utilization']:.2f}%")
    
    node2 = network.nodes.get("node2")
    if node2:
        storage_util = node2.get_storage_utilization()
        print(f"Storage utilization on node2: {storage_util['utilization_percent']:.2f}%")
    print("----------------------\n")
# ----------------------------------------

# Create network
network = StorageVirtualNetwork()

# Create nodes (500GB storage, 1000Mbps bandwidth)
node1 = StorageVirtualNode("node1", cpu_capacity=4, memory_capacity=16, storage_capacity=500, bandwidth=1000)
node2 = StorageVirtualNode("node2", cpu_capacity=8, memory_capacity=32, storage_capacity=1000, bandwidth=2000)

# Add nodes to network
network.add_node(node1)
network.add_node(node2)

# Connect nodes with 1Gbps link (1000 Mbps)
network.connect_nodes("node1", "node2", bandwidth=1000)

# Initiate file transfer (100MB file from node1 to node2)
file_size_bytes = 100 * 1024 * 1024
transfer = network.initiate_file_transfer(
    source_node_id="node1",
    target_node_id="node2",
    file_name="large_dataset.zip",
    file_size=file_size_bytes
)

if transfer:
    print(f"Transfer initiated: {transfer.file_id}")
    
    # Process transfer in chunks
    step_count = 0
    while True:
        step_count += 1
        chunks_done, completed = network.process_file_transfer(
            source_node_id="node1",
            target_node_id="node2",
            file_id=transfer.file_id,
            chunks_per_step=3  # Process 3 chunks at a time
        )
        
        print(f"Step {step_count}: Transferred {chunks_done} chunks, completed: {completed}")
        print_stats(network) # <--- Using the new helper function
        
        if completed:
            print(f"✅ Transfer of '{transfer.file_name}' ({file_size_bytes / (1024*1024):.2f}MB) completed successfully!")
            print(f"Total Virtual Time: {network.simulation_time:.4f} seconds")
            break
            
        # Added a small sleep here to slow down how fast the terminal simulates the transfer
        time.sleep(0.9)
        
        # Safety break if something goes wrong (not needed for the fix, but good practice)
        if step_count > 1000:
            print("🚨 Safety break: Too many steps. Exiting simulation.")
            break
else:
    print("❌ Transfer failed to initiate.")