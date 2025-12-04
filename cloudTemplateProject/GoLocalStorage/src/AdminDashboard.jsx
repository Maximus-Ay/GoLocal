import React, { useState, useEffect } from 'react';
import { 
  Server, Users, Activity, Database, Plus, Power, PowerOff, 
  Trash2, CheckCircle, XCircle, LogOut, Settings, AlertCircle,
  TrendingUp, HardDrive, Cpu, Wifi
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:5000';

const AdminDashboard = ({ username, onLogout }) => {
  const [activeTab, setActiveTab] = useState('nodes');
  const [nodes, setNodes] = useState([
    {
      node_id: 'node1',
      cpu_capacity: 4,
      memory_capacity: 16,
      storage_capacity: 500,
      bandwidth: 1000,
      active: true,
      health: 'healthy',
      used_storage: 50,
      cpu_usage: 35,
      uptime: '99.9%'
    },
    {
      node_id: 'node2',
      cpu_capacity: 8,
      memory_capacity: 32,
      storage_capacity: 1000,
      bandwidth: 2000,
      active: true,
      health: 'healthy',
      used_storage: 120,
      cpu_usage: 28,
      uptime: '99.8%'
    }
  ]);
  
  const [users, setUsers] = useState([]);
  const [paymentRequests, setPaymentRequests] = useState([]);
  const [showCreateNodeModal, setShowCreateNodeModal] = useState(false);
  const [newNode, setNewNode] = useState({
    node_id: '',
    cpu_capacity: 4,
    memory_capacity: 16,
    storage_capacity: 500,
    bandwidth: 1000
  });

  useEffect(() => {
    fetchUsers();
    fetchPaymentRequests();
    const interval = setInterval(() => {
      fetchUsers();
      fetchPaymentRequests();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/get-users`);
      const data = await response.json();
      if (response.ok && data.users) {
        setUsers(data.users);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchPaymentRequests = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/get-payment-requests`);
      const data = await response.json();
      if (response.ok && data.requests) {
        setPaymentRequests(data.requests);
      }
    } catch (error) {
      console.error('Failed to fetch payment requests:', error);
    }
  };

  const handleCreateNode = () => {
    if (!newNode.node_id.trim()) {
      alert('Please enter a node ID');
      return;
    }

    const node = {
      ...newNode,
      active: true,
      health: 'healthy',
      used_storage: 0,
      cpu_usage: 0,
      uptime: '100%'
    };

    setNodes(prev => [...prev, node]);
    setShowCreateNodeModal(false);
    setNewNode({
      node_id: '',
      cpu_capacity: 4,
      memory_capacity: 16,
      storage_capacity: 500,
      bandwidth: 1000
    });
    alert('✅ Node created successfully!');
  };

  const handleToggleNode = (nodeId) => {
    setNodes(prev => prev.map(node => 
      node.node_id === nodeId ? { ...node, active: !node.active } : node
    ));
  };

  const handleDeleteNode = (nodeId) => {
    if (!confirm(`Are you sure you want to delete ${nodeId}?`)) return;
    setNodes(prev => prev.filter(node => node.node_id !== nodeId));
    alert('✅ Node deleted successfully!');
  };

  const handleApprovePayment = async (request) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/approve-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: request.username,
          additional_storage_gb: request.storage_gb
        })
      });

      if (response.ok) {
        alert(`✅ Payment approved for ${request.username}!\n\n+${request.storage_gb}GB storage added.`);
        fetchPaymentRequests();
        fetchUsers();
      }
    } catch (error) {
      console.error('Failed to approve payment:', error);
      alert('❌ Failed to approve payment. Please try again.');
    }
  };

  const handleRejectPayment = async (requestId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/reject-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId })
      });

      if (response.ok) {
        alert('Payment request rejected.');
        fetchPaymentRequests();
      }
    } catch (error) {
      console.error('Failed to reject payment:', error);
    }
  };

  const getHealthColor = (health) => {
    switch(health) {
      case 'healthy': return '#4caf50';
      case 'warning': return '#ff9800';
      case 'critical': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  return (
    <>
      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        .admin-page { min-height: 100vh; background: #f5f5f5; }
        
        .admin-header {
          background: linear-gradient(135deg, #1976d2 0%, #2196f3 100%);
          padding: 20px 40px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header-left { display: flex; align-items: center; gap: 15px; color: white; }
        .admin-brand { font-size: 28px; font-weight: 800; }
        .admin-subtitle { font-size: 14px; opacity: 0.9; }
        .header-right { display: flex; align-items: center; gap: 20px; color: white; }
        
        .logout-btn {
          background: rgba(255, 255, 255, 0.2);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          transition: all 0.3s ease;
        }
        
        .logout-btn:hover { background: rgba(255, 255, 255, 0.3); }
        
        .admin-content { padding: 40px; max-width: 1400px; margin: 0 auto; }
        
        .tabs {
          display: flex;
          gap: 10px;
          margin-bottom: 30px;
          border-bottom: 2px solid #e0e0e0;
        }
        
        .tab {
          padding: 12px 24px;
          background: none;
          border: none;
          cursor: pointer;
          font-weight: 600;
          color: #666;
          display: flex;
          align-items: center;
          gap: 8px;
          border-bottom: 3px solid transparent;
          transition: all 0.3s ease;
        }
        
        .tab.active {
          color: #2196f3;
          border-bottom-color: #2196f3;
        }
        
        .tab:hover { color: #2196f3; }
        
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 30px;
        }
        
        .section-title { font-size: 28px; font-weight: 700; color: #1565c0; }
        
        .btn-primary {
          padding: 12px 24px;
          background: linear-gradient(135deg, #1976d2 0%, #2196f3 100%);
          color: white;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(33, 150, 243, 0.3);
        }
        
        .nodes-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 25px;
        }
        
        .node-card {
          background: white;
          border-radius: 16px;
          padding: 25px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
          transition: all 0.3s ease;
        }
        
        .node-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }
        
        .node-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        
        .node-title {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .node-title h3 {
          font-size: 20px;
          font-weight: 700;
          color: #1565c0;
        }
        
        .node-status {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .node-actions {
          display: flex;
          gap: 8px;
        }
        
        .icon-btn {
          width: 36px;
          height: 36px;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }
        
        .icon-btn.power { background: #e3f2fd; color: #2196f3; }
        .icon-btn.power.off { background: #ffebee; color: #f44336; }
        .icon-btn.delete { background: #ffebee; color: #f44336; }
        .icon-btn:hover { transform: scale(1.1); }
        
        .node-stats {
          display: grid;
          gap: 15px;
        }
        
        .stat-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 0;
          border-bottom: 1px solid #f0f0f0;
        }
        
        .stat-row:last-child { border-bottom: none; }
        
        .stat-label {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #666;
          font-size: 14px;
        }
        
        .stat-value {
          font-weight: 700;
          color: #333;
          font-size: 15px;
        }
        
        .health-badge {
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 700;
          color: white;
        }
        
        .users-table,
        .payments-table {
          background: white;
          border-radius: 16px;
          padding: 25px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        table {
          width: 100%;
          border-collapse: collapse;
        }
        
        th {
          text-align: left;
          padding: 15px;
          background: #f5f5f5;
          font-weight: 700;
          color: #333;
          font-size: 14px;
        }
        
        td {
          padding: 15px;
          border-bottom: 1px solid #f0f0f0;
          color: #666;
        }
        
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #f9f9f9; }
        
        .action-btns {
          display: flex;
          gap: 8px;
        }
        
        .btn-approve {
          padding: 6px 16px;
          background: #4caf50;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        
        .btn-reject {
          padding: 6px 16px;
          background: #f44336;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        
        .modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        
        .modal-content {
          background: white;
          border-radius: 20px;
          padding: 40px;
          max-width: 500px;
          width: 100%;
        }
        
        .modal-title {
          font-size: 24px;
          font-weight: 700;
          color: #1565c0;
          margin-bottom: 25px;
        }
        
        .form-group {
          margin-bottom: 20px;
        }
        
        .form-group label {
          display: block;
          font-weight: 600;
          color: #333;
          margin-bottom: 8px;
          font-size: 14px;
        }
        
        .form-group input,
        .form-group select {
          width: 100%;
          padding: 12px 15px;
          border: 2px solid #e0e0e0;
          border-radius: 10px;
          font-size: 15px;
        }
        
        .form-group input:focus,
        .form-group select:focus {
          outline: none;
          border-color: #2196f3;
        }
        
        .modal-buttons {
          display: flex;
          gap: 15px;
          margin-top: 30px;
        }
        
        .btn-cancel {
          flex: 1;
          padding: 12px;
          background: #f5f5f5;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
        }
        
        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #999;
        }
        
        .empty-icon {
          width: 80px;
          height: 80px;
          background: #f5f5f5;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
        }
        
        @media (max-width: 768px) {
          .admin-header { flex-direction: column; gap: 15px; }
          .admin-content { padding: 20px; }
          .nodes-grid { grid-template-columns: 1fr; }
          table { font-size: 13px; }
        }
      `}</style>

      <div className="admin-page">
        <div className="admin-header">
          <div className="header-left">
            <Settings size={32} />
            <div>
              <div className="admin-brand">Admin Dashboard</div>
              <div className="admin-subtitle">System Management</div>
            </div>
          </div>
          <div className="header-right">
            <span>Admin: {username}</span>
            <button className="logout-btn" onClick={onLogout}>
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </div>

        <div className="admin-content">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'nodes' ? 'active' : ''}`}
              onClick={() => setActiveTab('nodes')}
            >
              <Server size={18} />
              Nodes
            </button>
            <button 
              className={`tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              <Users size={18} />
              Users
            </button>
            <button 
              className={`tab ${activeTab === 'payments' ? 'active' : ''}`}
              onClick={() => setActiveTab('payments')}
            >
              <Activity size={18} />
              Payment Requests ({paymentRequests.length})
            </button>
          </div>

          {activeTab === 'nodes' && (
            <div>
              <div className="section-header">
                <h2 className="section-title">Network Nodes</h2>
                <button className="btn-primary" onClick={() => setShowCreateNodeModal(true)}>
                  <Plus size={18} />
                  Create Node
                </button>
              </div>

              <div className="nodes-grid">
                {nodes.map((node) => (
                  <div key={node.node_id} className="node-card">
                    <div className="node-header">
                      <div className="node-title">
                        <h3>{node.node_id}</h3>
                        <div 
                          className="node-status" 
                          style={{ background: node.active ? '#4caf50' : '#f44336' }}
                        ></div>
                      </div>
                      <div className="node-actions">
                        <button 
                          className={`icon-btn power ${!node.active ? 'off' : ''}`}
                          onClick={() => handleToggleNode(node.node_id)}
                          title={node.active ? 'Deactivate' : 'Activate'}
                        >
                          {node.active ? <Power size={18} /> : <PowerOff size={18} />}
                        </button>
                        <button 
                          className="icon-btn delete"
                          onClick={() => handleDeleteNode(node.node_id)}
                          title="Delete Node"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>

                    <div className="node-stats">
                      <div className="stat-row">
                        <div className="stat-label">
                          <Cpu size={16} />
                          CPU
                        </div>
                        <div className="stat-value">{node.cpu_capacity} vCPUs ({node.cpu_usage}%)</div>
                      </div>

                      <div className="stat-row">
                        <div className="stat-label">
                          <Database size={16} />
                          Memory
                        </div>
                        <div className="stat-value">{node.memory_capacity} GB</div>
                      </div>

                      <div className="stat-row">
                        <div className="stat-label">
                          <HardDrive size={16} />
                          Storage
                        </div>
                        <div className="stat-value">
                          {node.used_storage}/{node.storage_capacity} GB
                        </div>
                      </div>

                      <div className="stat-row">
                        <div className="stat-label">
                          <Wifi size={16} />
                          Bandwidth
                        </div>
                        <div className="stat-value">{node.bandwidth} Mbps</div>
                      </div>

                      <div className="stat-row">
                        <div className="stat-label">
                          <TrendingUp size={16} />
                          Uptime
                        </div>
                        <div className="stat-value">{node.uptime}</div>
                      </div>

                      <div className="stat-row">
                        <div className="stat-label">
                          <AlertCircle size={16} />
                          Health
                        </div>
                        <span 
                          className="health-badge" 
                          style={{ background: getHealthColor(node.health) }}
                        >
                          {node.health.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div>
              <div className="section-header">
                <h2 className="section-title">User Management</h2>
              </div>

              <div className="users-table">
                {users.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">
                      <Users size={40} color="#bbb" />
                    </div>
                    <p>No users found</p>
                  </div>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Storage Used</th>
                        <th>Total Quota</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user, index) => (
                        <tr key={index}>
                          <td><strong>{user.username}</strong></td>
                          <td>{user.email}</td>
                          <td>{user.used_quota_gb} GB</td>
                          <td>{user.total_quota_gb} GB</td>
                          <td>
                            <span 
                              className="health-badge" 
                              style={{ 
                                background: user.used_quota_gb / user.total_quota_gb >= 0.9 ? '#f44336' : '#4caf50' 
                              }}
                            >
                              {user.used_quota_gb / user.total_quota_gb >= 0.9 ? 'FULL' : 'ACTIVE'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {activeTab === 'payments' && (
            <div>
              <div className="section-header">
                <h2 className="section-title">Pending Payment Requests</h2>
              </div>

              <div className="payments-table">
                {paymentRequests.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">
                      <Activity size={40} color="#bbb" />
                    </div>
                    <p>No pending payment requests</p>
                  </div>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Storage Requested</th>
                        <th>Price</th>
                        <th>Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentRequests.map((request, index) => (
                        <tr key={index}>
                          <td><strong>{request.username}</strong></td>
                          <td>+{request.storage_gb} GB</td>
                          <td>{request.price.toLocaleString()} XAF</td>
                          <td>{new Date(request.date).toLocaleDateString()}</td>
                          <td>
                            <div className="action-btns">
                              <button 
                                className="btn-approve"
                                onClick={() => handleApprovePayment(request)}
                              >
                                <CheckCircle size={14} />
                                Approve
                              </button>
                              <button 
                                className="btn-reject"
                                onClick={() => handleRejectPayment(request.id)}
                              >
                                <XCircle size={14} />
                                Reject
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>

        {showCreateNodeModal && (
          <div className="modal">
            <div className="modal-content">
              <h2 className="modal-title">Create New Node</h2>
              
              <div className="form-group">
                <label>Node ID</label>
                <input
                  type="text"
                  placeholder="e.g., node3"
                  value={newNode.node_id}
                  onChange={(e) => setNewNode({...newNode, node_id: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>CPU Capacity (vCPUs)</label>
                <input
                  type="number"
                  value={newNode.cpu_capacity}
                  onChange={(e) => setNewNode({...newNode, cpu_capacity: parseInt(e.target.value)})}
                />
              </div>

              <div className="form-group">
                <label>Memory (GB)</label>
                <input
                  type="number"
                  value={newNode.memory_capacity}
                  onChange={(e) => setNewNode({...newNode, memory_capacity: parseInt(e.target.value)})}
                />
              </div>

              <div className="form-group">
                <label>Storage (GB)</label>
                <input
                  type="number"
                  value={newNode.storage_capacity}
                  onChange={(e) => setNewNode({...newNode, storage_capacity: parseInt(e.target.value)})}
                />
              </div>

              <div className="form-group">
                <label>Bandwidth (Mbps)</label>
                <input
                  type="number"
                  value={newNode.bandwidth}
                  onChange={(e) => setNewNode({...newNode, bandwidth: parseInt(e.target.value)})}
                />
              </div>

              <div className="modal-buttons">
                <button 
                  className="btn-cancel"
                  onClick={() => setShowCreateNodeModal(false)}
                >
                  Cancel
                </button>
                <button 
                  className="btn-primary"
                  onClick={handleCreateNode}
                  style={{ flex: 1 }}
                >
                  Create Node
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default AdminDashboard;