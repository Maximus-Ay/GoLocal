from typing import Dict, List, Optional, Tuple, Union
import hashlib
import time
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus, User 
from collections import defaultdict

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.simulation_time: float = 0.0 # DES FIX: Global Simulation Clock
        self.users: Dict[str, User] = {} # NEW: User Registry
        
    def add_node(self, node: StorageVirtualNode):
        """Add a node to the network"""
        self.nodes[node.node_id] = node

    def add_user(self, user: User): 
        """Add a user to the network"""
        self.users[user.user_id] = user

    def get_user_quota_info(self, user_id: str) -> Optional[User]:
        """Returns the User object."""
        return self.users.get(user_id)
        
    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth: int):
        """Connect two nodes with specified bandwidth"""
        if node1_id in self.nodes and node2_id in self.nodes:
            self.nodes[node1_id].add_connection(node2_id, bandwidth)
            self.nodes[node2_id].add_connection(node1_id, bandwidth)
            return True
        return False
    
    def initiate_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_name: str,
        file_size: int,
        user_id: str # NEW: Required user_id
    ) -> Optional[FileTransfer]:
        """Initiate a file transfer between nodes, checking user quota"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            return None
            
        # --- User Validation and Quota Check (CRITICAL) ---
        user = self.users.get(user_id)
        if not user:
            print(f"❌ Transfer Failed: User ID '{user_id}' not found.")
            return None
        
        if user.used_quota + file_size > user.total_quota:
            print(f"❌ Transfer Failed: User '{user.name}' quota exceeded. Needed: {file_size / 1024**2:.2f}MB, Available: {(user.total_quota - user.used_quota) / 1024**2:.2f}MB") 
            return None
        # ----------------------------------------

        # Generate unique file ID
        file_id = hashlib.md5(f"{file_name}-{time.time()}".encode()).hexdigest()
        
        # Request storage on target node (pass user_id)
        target_node = self.nodes[target_node_id]
        transfer = target_node.initiate_transfer(file_id, file_name, file_size, user_id) 
        
        if transfer:
            self.transfer_operations[source_node_id][file_id] = transfer
            return transfer
        return None
    
    def process_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_id: str,
        chunks_per_step: int = 1
    ) -> Tuple[int, bool]:
        """Process a file transfer in chunks"""
        target_node = self.nodes.get(target_node_id)
        source_node = self.nodes.get(source_node_id)
        transfer = self.transfer_operations.get(source_node_id, {}).get(file_id)

        if not transfer or not target_node or not source_node:
            return (0, False)
            
        chunks_transferred = 0
        time_spent_in_step = 0.0 

        for chunk in transfer.chunks:
            if chunk.status != TransferStatus.COMPLETED and chunks_transferred < chunks_per_step:
                
                # Call node method, which returns (success: bool, time_spent: float)
                success, transfer_time = target_node.process_chunk_transfer(
                    file_id, chunk.chunk_id, source_node_id
                ) 
                
                if success:
                    chunks_transferred += 1
                    time_spent_in_step += transfer_time # Aggregate the DES time
                else:
                    return (chunks_transferred, False) 
        
        # Advance the simulation clock after the step is complete
        self.simulation_time += time_spent_in_step # Update global clock

        # Check if transfer is complete
        if all(c.status == TransferStatus.COMPLETED for c in transfer.chunks):
            transfer.status = TransferStatus.COMPLETED
            
            # --- Update User Quota ---
            user = self.users.get(transfer.user_id)
            if user:
                user.used_quota += transfer.total_size
            # -------------------------------
            
            # Clean up
            if file_id in self.transfer_operations[source_node_id]:
                 del self.transfer_operations[source_node_id][file_id]
            if file_id in source_node.active_transfers:
                del source_node.active_transfers[file_id]
                
            return (chunks_transferred, True)
            
        return (chunks_transferred, False)
    
    def get_network_stats(self) -> Dict[str, Union[int, float]]: 
        """Get overall network statistics, including simulation time"""
        total_bandwidth = sum(n.bandwidth for n in self.nodes.values())
        used_bandwidth = sum(n.network_utilization for n in self.nodes.values())
        total_storage = sum(n.total_storage for n in self.nodes.values())
        used_storage = sum(n.used_storage for n in self.nodes.values())
        
        return {
            "total_nodes": len(self.nodes),
            "total_bandwidth_bps": total_bandwidth,
            "used_bandwidth_bps": used_bandwidth,
            "bandwidth_utilization": (used_bandwidth / total_bandwidth) * 100 if total_bandwidth else 0,
            "total_storage_bytes": total_storage,
            "used_storage_bytes": used_storage,
            "storage_utilization": (used_storage / total_storage) * 100 if total_storage else 0,
            "active_transfers": sum(len(t) for t in self.transfer_operations.values()),
            "simulation_time_seconds": self.simulation_time 
        }