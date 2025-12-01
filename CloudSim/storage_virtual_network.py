from typing import Dict, List, Optional, Tuple, Union
import hashlib
import time
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus
from collections import defaultdict

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.simulation_time: float = 0.0 # Global Simulation Clock
        
    def add_node(self, node: StorageVirtualNode):
        """Add a node to the network"""
        self.nodes[node.node_id] = node
        
    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth: int):
        """Connect two nodes with specified bandwidth (in Mbps)"""
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
        file_size: int
    ) -> Optional[FileTransfer]:
        """Initiate a file transfer between nodes"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            return None
            
        # Generate unique file ID
        file_id = hashlib.md5(f"{file_name}-{time.time()}".encode()).hexdigest()

        # 1. Target node prepares to receive file (creates transfer object)
        target_node = self.nodes[target_node_id]
        transfer = target_node.initiate_transfer(file_id, file_name, file_size)
        
        if transfer:
            # 2. Source node also tracks the transfer (to use its bandwidth info)
            source_node = self.nodes[source_node_id]
            source_node.active_transfers[file_id] = transfer
            
            self.transfer_operations[source_node_id][file_id] = transfer
        
        return transfer

    def process_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_id: str,
        chunks_per_step: int = 1
    ) -> Tuple[int, bool]:
        """
        Process a set of file chunks for a transfer operation.
        Returns: (chunks_processed_in_this_step, is_completed)
        """
        target_node = self.nodes.get(target_node_id)
        if not target_node:
            return (0, False)

        transfer = self.transfer_operations.get(source_node_id, {}).get(file_id)
        if not transfer:
            return (0, False)

        chunks_transferred = 0
        time_spent_in_step = 0.0 # Tracker for time spent in this step

        # Iterate through file chunks
        for chunk in transfer.chunks:
            if chunk.status != TransferStatus.COMPLETED and chunks_transferred < chunks_per_step:
                
                # Call node method, which now returns (success: bool, time_spent: float)
                success, transfer_time = target_node.process_chunk_transfer(
                    file_id, chunk.chunk_id, source_node_id
                )
                
                if success:
                    chunks_transferred += 1
                    time_spent_in_step += transfer_time # NEW: Aggregate the time
                else:
                    # If any chunk fails, return immediately
                    return (chunks_transferred, False)
        
        # Advance the simulation clock after the step is complete
        self.simulation_time += time_spent_in_step # <--- NEW: Update global clock

        # Check if transfer is complete
        if all(c.status == TransferStatus.COMPLETED for c in transfer.chunks):
            transfer.status = TransferStatus.COMPLETED
            
            # Clean up from network tracking
            if file_id in self.transfer_operations.get(source_node_id, {}):
                del self.transfer_operations[source_node_id][file_id]
            
            # Clean up from source node tracking
            source_node = self.nodes.get(source_node_id)
            if source_node and file_id in source_node.active_transfers:
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
            "active_transfers": sum(len(d) for d in self.transfer_operations.values()),
            "simulation_time_seconds": self.simulation_time # NEW: Report time
        }