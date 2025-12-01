import time
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Tuple
from enum import Enum, auto
import hashlib

class TransferStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

# --- NEW: User Dataclass for Quota Management ---
@dataclass
class User:
    user_id: str
    name: str
    # Default 100MB Quota for initial testing (adjust this later, e.g., to 2*1024**3 for 2GB)
    total_quota: int = 100 * 1024 * 1024 
    used_quota: int = 0
# --------------------------------------------------

@dataclass
class FileChunk:
    chunk_id: int
    size: int  # in bytes
    checksum: str
    status: TransferStatus = TransferStatus.PENDING
    stored_node: Optional[str] = None

@dataclass
class FileTransfer:
    file_id: str
    file_name: str
    total_size: int  # in bytes
    user_id: str # <--- NEW: Associate transfer with a user
    chunks: List[FileChunk]
    status: TransferStatus = TransferStatus.PENDING
    created_at: float = time.time()
    completed_at: Optional[float] = None

class StorageVirtualNode:
    def __init__(
        self,
        node_id: str,
        cpu_capacity: int,  # in vCPUs
        memory_capacity: int,  # in GB
        storage_capacity: int,  # in GB
        bandwidth: int  # in Mbps
    ):
        self.node_id = node_id
        self.cpu_capacity = cpu_capacity
        self.memory_capacity = memory_capacity
        self.total_storage = storage_capacity * 1024 * 1024 * 1024  # Convert GB to bytes
        self.bandwidth = bandwidth * 1000000  # Convert Mbps to bits per second
        
        # Current utilization
        self.used_storage = 0
        self.network_utilization = 0  # in bits per second (bps)
        self.total_data_transferred = 0
        self.total_requests_processed = 0
        self.failed_requests = 0
        
        # Data structures
        self.active_transfers: Dict[str, FileTransfer] = {}
        self.stored_files: Dict[str, FileTransfer] = {} 
        self.connections: Dict[str, int] = {} # {node_id: bandwidth_bps}

    def add_connection(self, target_node_id: str, bandwidth_mbps: int):
        """Add a connection and its bandwidth in bits per second"""
        self.connections[target_node_id] = bandwidth_mbps * 1000000
    
    def _calculate_chunk_size(self, file_size: int) -> int:
        """Determines optimal chunk size based on file size (Adaptive Chunking)"""
        if file_size <= 2 * 1024 * 1024:
            return 512 * 1024  # 512KB for small files
        elif file_size <= 50 * 1024 * 1024:
            return 2 * 1024 * 1024  # 2MB
        else:
            return 10 * 1024 * 1024 # 10MB
    
    def _generate_chunks(self, file_id: str, file_size: int) -> List[FileChunk]:
        """Breaks a file into chunks for transfer"""
        chunk_size = self._calculate_chunk_size(file_size)
        
        return [
            FileChunk(
                chunk_id=i,
                size=min(chunk_size, file_size - i*chunk_size),
                checksum=hashlib.md5(f"{file_id}-{i}".encode()).hexdigest()
            )
            for i in range(math.ceil(file_size/chunk_size))
        ]

    def initiate_transfer(self, file_id: str, file_name: str, file_size: int, user_id: str) -> Optional[FileTransfer]:
        """Initializes a new transfer and allocates storage if target node"""
        
        # Node capacity check (The network will handle user quota)
        if self.used_storage + file_size > self.total_storage:
            print(f"🛑 Node {self.node_id} Storage Full! Cannot accept file {file_id}.")
            return None
        
        chunks = self._generate_chunks(file_id, file_size)
        transfer = FileTransfer(
            file_id=file_id,
            file_name=file_name,
            total_size=file_size,
            user_id=user_id, # <--- Pass User ID
            chunks=chunks,
            status=TransferStatus.PENDING
        )
        self.active_transfers[file_id] = transfer
        
        return transfer

    def process_chunk_transfer(
        self,
        file_id: str,
        chunk_id: int,
        source_node_id: str
    ) -> Tuple[bool, float]: # <--- DES FIX: Now returns (Success Status, Time Spent)
        """
        Simulates the transfer of a single file chunk to this node.
        Returns a tuple: (success: bool, time_spent: float)
        """
        self.total_requests_processed += 1
        transfer_time = 0.0 
        
        if file_id not in self.active_transfers:
            self.failed_requests += 1
            return (False, 0.0) 

        transfer = self.active_transfers[file_id]
        
        try:
            chunk = next(c for c in transfer.chunks if c.chunk_id == chunk_id)
        except StopIteration:
            self.failed_requests += 1
            return (False, 0.0)
            
        # Get connection bandwidth
        connection_bandwidth = self.connections.get(source_node_id)
        if connection_bandwidth is None:
            self.failed_requests += 1
            return (False, 0.0) 
        
        # Calculate chunk size in bits
        chunk_size_bits = chunk.size * 8
        available_bandwidth = connection_bandwidth
        
        if available_bandwidth <= 0:
            self.failed_requests += 1
            return (False, 0.0)
            
        # Calculate transfer time (in seconds)
        transfer_time = chunk_size_bits / available_bandwidth
        
        # >>> CRITICAL DES CHANGE: REMOVED time.sleep(transfer_time) <<<
        
        # Update node metrics (simulate network load for the duration)
        self.network_utilization = available_bandwidth
        
        # Update chunk status
        chunk.status = TransferStatus.COMPLETED
        chunk.stored_node = self.node_id
        
        # Update storage and transfer metrics
        self.used_storage += chunk.size
        self.total_data_transferred += chunk.size
        
        # Check if file is complete (will be finalized by the Network)
        if all(c.status == TransferStatus.COMPLETED for c in transfer.chunks):
            transfer.status = TransferStatus.COMPLETED
            transfer.completed_at = time.time()
            self.stored_files[file_id] = transfer
            
        # Reset network utilization right after the event
        self.network_utilization = 0
            
        return (True, transfer_time) # <--- DES FIX: Return success and time spent

    def get_user_storage_on_node(self, user_id: str) -> int:
        """Calculates the total storage used by a specific user on this node."""
        return sum(
            t.total_size 
            for t in self.stored_files.values() 
            if t.user_id == user_id
        )

    def get_storage_utilization(self) -> Dict[str, Union[int, float, List[str]]]:
        """Get current storage utilization metrics"""
        return {
            "used_bytes": self.used_storage,  # int
            "total_bytes": self.total_storage,  # int
            "utilization_percent": (self.used_storage / self.total_storage) * 100 if self.total_storage else 0,  # float
            "files_stored": len(self.stored_files),  # int
            "active_transfers": len(self.active_transfers)  # int
        }

    def get_network_utilization(self) -> Dict[str, Union[int, float, List[str]]]:
        """Get current network utilization metrics"""
        total_bandwidth_bps = self.bandwidth
        return {
            "current_utilization_bps": self.network_utilization,  # float
            "max_bandwidth_bps": total_bandwidth_bps,  # int
            "utilization_percent": (self.network_utilization / total_bandwidth_bps) * 100 if total_bandwidth_bps else 0,  # float
            "connections": list(self.connections.keys())  # List[str]
        }

    def get_performance_metrics(self) -> Dict[str, int]:
        """Get node performance metrics"""
        return {
            "total_requests_processed": self.total_requests_processed,
            "total_data_transferred_bytes": self.total_data_transferred,
            "failed_transfers": self.failed_requests
        }