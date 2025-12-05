import sys
import grpc
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

import cloudsecurity_pb2
import cloudsecurity_pb2_grpc

GRPC_SERVER_ADDRESS = 'localhost:51234'

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# In-memory storage for payment requests and user files
payment_requests = []
user_files = {}
users_registry = {}

# NEW: Chunk distribution tracking
# Structure: { 'node_id': { 'chunk_count': X, 'files': ['file1', 'file2'], 'active': True } }
nodes_registry = {
    'node1': {'chunk_count': 0, 'files': [], 'active': True, 'chunks': []},
    'node2': {'chunk_count': 0, 'files': [], 'active': True, 'chunks': []},
    'node3': {'chunk_count': 0, 'files': [], 'active': True, 'chunks': []}
}

# Track file chunks: { 'file_id': { 'filename': 'x', 'total_chunks': N, 'distribution': { 'node1': [1,2,3], 'node2': [4,5] } } }
file_chunks_registry = {}

def distribute_chunks_to_nodes(file_id, filename, file_size_mb, total_chunks):
    """
    Distributes file chunks across active nodes using round-robin.
    Returns the distribution map.
    """
    active_nodes = [node_id for node_id, data in nodes_registry.items() if data['active']]
    
    if not active_nodes:
        return {}
    
    distribution = {node_id: [] for node_id in active_nodes}
    
    # Round-robin distribution
    for chunk_num in range(total_chunks):
        node_id = active_nodes[chunk_num % len(active_nodes)]
        distribution[node_id].append(chunk_num + 1)
    
    # Update nodes registry
    for node_id, chunks in distribution.items():
        nodes_registry[node_id]['chunk_count'] += len(chunks)
        nodes_registry[node_id]['chunks'].extend([{'file_id': file_id, 'chunk_nums': chunks}])
        if filename not in nodes_registry[node_id]['files']:
            nodes_registry[node_id]['files'].append(filename)
    
    # Store in file chunks registry
    file_chunks_registry[file_id] = {
        'filename': filename,
        'file_size_mb': file_size_mb,
        'total_chunks': total_chunks,
        'distribution': distribution
    }
    
    return distribution

def calculate_chunk_count(file_size_mb):
    """Calculate number of chunks based on file size (similar to backend logic)"""
    file_size_bytes = file_size_mb * 1024 * 1024
    
    if file_size_bytes <= 2 * 1024 * 1024:  # <= 2MB
        chunk_size = 512 * 1024  # 512KB
    elif file_size_bytes <= 50 * 1024 * 1024:  # <= 50MB
        chunk_size = 2 * 1024 * 1024  # 2MB
    else:
        chunk_size = 10 * 1024 * 1024  # 10MB
    
    import math
    return math.ceil(file_size_bytes / chunk_size)

def get_grpc_stub():
    channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
    stub = cloudsecurity_pb2_grpc.UserServiceStub(channel)
    return stub

@app.route('/api/grpc-call', methods=['POST'])
def grpc_call_handler():
    try:
        data = request.get_json()
        command = data.get('command')
        params = data.get('params', {})
    except Exception:
        return jsonify({"result": "Error: Invalid JSON payload.", "type": "ERROR"}), 400

    if not command:
        return jsonify({"result": "Error: 'command' field is missing.", "type": "ERROR"}), 400

    stub = get_grpc_stub()
    response = None

    try:
        if command == "signup":
            if all(k in params for k in ('username', 'email', 'password')):
                response = stub.signup(cloudsecurity_pb2.SignupRequest(
                    login=params['username'],
                    email=params['email'],
                    password=params['password']
                ))
                
                if response and "success" in response.result.lower():
                    users_registry[params['username']] = {
                        'username': params['username'],
                        'email': params['email'],
                        'used_quota_gb': 0.0,
                        'total_quota_gb': 2.0,
                        'created_at': datetime.now().isoformat()
                    }
            else:
                raise ValueError("Missing parameters for signup.")

        elif command == "login":
            if all(k in params for k in ('username', 'password')):
                response = stub.login(cloudsecurity_pb2.Request(
                    login=params['username'],
                    password=params['password']
                ))
            else:
                raise ValueError("Missing parameters for login.")

        elif command == "verify_otp":
            if all(k in params for k in ('username', 'otp')):
                response = stub.verify_otp(cloudsecurity_pb2.VerificationRequest(
                    login=params['username'],
                    otp=str(params['otp'])
                ))
            else:
                raise ValueError("Missing parameters for verify_otp.")

        elif command == "status":
            if 'username' in params:
                response = stub.get_status(cloudsecurity_pb2.Request(
                    login=params['username']
                ))
            else:
                raise ValueError("Missing parameter 'username' for status.")

        elif command == "upload_file":
            if all(k in params for k in ('username', 'file_name', 'file_size_mb')):
                file_size_mb = float(params['file_size_mb'])
                file_size_bytes = int(file_size_mb * 1024 * 1024)

                response = stub.upload_file(cloudsecurity_pb2.Request(
                    login=params['username'],
                    file_name=params['file_name'],
                    file_size=file_size_bytes
                ))
                
                username = params['username']
                if username not in user_files:
                    user_files[username] = []
                
                file_name = params['file_name']
                file_extension = file_name.split('.')[-1].upper() if '.' in file_name else 'FILE'
                file_id = f"{username}-{file_name}-{int(datetime.now().timestamp())}"

                user_files[username].append({
                    'id': file_name,
                    'name': file_name,
                    'size': f"{file_size_mb:.2f}",
                    'timestamp': datetime.now().isoformat(),
                    'extension': file_extension
                })
                
                # NEW: Distribute chunks across nodes
                total_chunks = calculate_chunk_count(file_size_mb)
                distribution = distribute_chunks_to_nodes(file_id, file_name, file_size_mb, total_chunks)
                
                print(f"📦 File '{file_name}' broken into {total_chunks} chunks")
                print(f"📍 Distribution: {distribution}")
                
                if username in users_registry:
                    users_registry[username]['used_quota_gb'] += file_size_mb / 1024
            else:
                raise ValueError("Missing parameters for upload_file.")

        else:
            return jsonify({
                "result": f"Error: Unknown command '{command}'.", 
                "type": "ERROR"
            }), 400

        if response:
            return jsonify({
                "result": response.result,
                "session_token": response.session_token if hasattr(response, 'session_token') else '',
                "type": "SUCCESS" if "success" in response.result.lower() or "verified" in response.result.lower() else "INFO"
            }), 200

    except grpc.RpcError as e:
        return jsonify({
            "result": f"gRPC Error: {e.details()}",
            "type": "ERROR"
        }), 500
        
    except ValueError as e:
        return jsonify({
            "result": f"Parameter Error: {str(e)}", 
            "type": "ERROR"
        }), 400
        
    except Exception as e:
        return jsonify({
            "result": f"Internal Server Error: {str(e)}", 
            "type": "ERROR"
        }), 500

@app.route('/api/get-user-files', methods=['POST'])
def get_user_files():
    try:
        data = request.get_json()
        username = data.get('username')
        files = user_files.get(username, [])
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== FILE MANAGEMENT ENDPOINTS ====================

@app.route('/api/rename-file', methods=['POST'])
def rename_file():
    try:
        data = request.get_json()
        username = data.get('username')
        old_file_id = data.get('file_id') 
        new_file_name = data.get('new_file_name')
        
        if not all([username, old_file_id, new_file_name]):
            return jsonify({"error": "Missing parameters"}), 400

        if username not in user_files:
            return jsonify({"error": "User has no files"}), 404
        
        found = False
        for file in user_files[username]:
            if file['id'] == old_file_id:
                file['name'] = new_file_name
                file['id'] = new_file_name 
                file['extension'] = new_file_name.split('.')[-1].upper() if '.' in new_file_name else 'FILE'
                found = True
                break
        
        if found:
            print(f"📄 File renamed: {old_file_id} -> {new_file_name}")
            return jsonify({"success": True, "message": f"File renamed to {new_file_name}"}), 200
        else:
            return jsonify({"error": f"File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    try:
        data = request.get_json()
        username = data.get('username')
        file_id = data.get('file_id') 
        file_size_mb = data.get('file_size_mb')
        
        if not all([username, file_id, file_size_mb is not None]):
            return jsonify({"error": "Missing parameters"}), 400

        if username not in user_files:
            return jsonify({"error": "User has no files"}), 404
        
        initial_file_count = len(user_files[username])
        
        # Find and remove file chunks from nodes
        file_to_delete = None
        for file in user_files[username]:
            if file['id'] == file_id:
                file_to_delete = file
                break
        
        # Remove chunks from nodes registry
        if file_to_delete:
            for node_id, node_data in nodes_registry.items():
                # Remove file from node's file list
                if file_to_delete['name'] in node_data['files']:
                    node_data['files'].remove(file_to_delete['name'])
                
                # Remove and count chunks for this file
                chunks_to_remove = [chunk for chunk in node_data['chunks'] if file_to_delete['name'] in chunk.get('file_id', '')]
                for chunk in chunks_to_remove:
                    node_data['chunk_count'] -= len(chunk.get('chunk_nums', []))
                    node_data['chunks'].remove(chunk)
        
        user_files[username] = [file for file in user_files[username] if file['id'] != file_id]
        deleted_count = initial_file_count - len(user_files[username])
        
        if deleted_count > 0:
            if username in users_registry:
                quota_to_reduce = file_size_mb / 1024
                users_registry[username]['used_quota_gb'] = max(0, users_registry[username]['used_quota_gb'] - quota_to_reduce)
            
            print(f"🗑️ File deleted: {file_id}")
            return jsonify({"success": True, "message": f"File deleted successfully"}), 200
        else:
            return jsonify({"error": f"File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== STORAGE REQUEST ENDPOINT ====================

@app.route('/api/request-storage', methods=['POST'])
def request_storage():
    try:
        data = request.get_json()
        username = data.get('username')
        additional_storage_gb = data.get('additional_storage_gb')
        price = data.get('price')
        payment_details = data.get('payment_details')
        
        if not all([username, additional_storage_gb, price, payment_details]):
            return jsonify({"result": "Missing required fields"}), 400

        request_id = f"PAY-{int(datetime.now().timestamp())}"
        
        new_request = {
            "id": request_id,
            "username": username,
            "storage_gb": additional_storage_gb,
            "price": price,
            "payment_details": payment_details,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        payment_requests.append(new_request)
        print(f"💳 New storage request: {request_id}")
        return jsonify({"result": "Payment request submitted successfully", "request_id": request_id}), 200

    except Exception as e:
        return jsonify({"result": "Internal server error", "error": str(e)}), 500

# ==================== USER QUOTA ENDPOINT ====================

@app.route('/api/get-user-quota/<username>', methods=['GET'])
def get_user_quota(username):
    try:
        user = users_registry.get(username)
        if user:
            quota_mb = {
                'used': round(user['used_quota_gb'] * 1024, 2), 
                'total': user['total_quota_gb'] * 1024          
            }
            return jsonify(quota_mb), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/get-users', methods=['GET'])
def get_users():
    try:
        users_list = list(users_registry.values())
        if not users_list:
            users_list = [
                {
                    "username": "demo_user",
                    "email": "demo@example.com",
                    "used_quota_gb": 0.5,
                    "total_quota_gb": 2.0
                }
            ]
        
        print(f"📊 Admin requested users: {len(users_list)} users")
        return jsonify({"users": users_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/get-payment-requests', methods=['GET'])
def get_payment_requests():
    try:
        pending = [req for req in payment_requests if req['status'] == 'pending']
        print(f"💳 Admin requested payments: {len(pending)} pending")
        return jsonify({"requests": pending}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/approve-payment', methods=['POST'])
def approve_payment():
    try:
        data = request.get_json()
        username = data.get('username')
        storage_gb = data.get('additional_storage_gb')
        
        print(f"✅ Approving payment for {username}: +{storage_gb}GB")
        
        for req in payment_requests:
            if req['username'] == username and req['status'] == 'pending':
                req['status'] = 'approved'
                break
        
        if username in users_registry:
            users_registry[username]['total_quota_gb'] += storage_gb
            print(f"   New quota: {users_registry[username]['total_quota_gb']}GB")
        
        return jsonify({"result": "Payment approved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/reject-payment', methods=['POST'])
def reject_payment():
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        
        print(f"❌ Rejecting payment: {request_id}")
        
        for req in payment_requests:
            if req['id'] == request_id:
                req['status'] = 'rejected'
                break
        
        return jsonify({"result": "Payment rejected"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== NEW: NODE MANAGEMENT ENDPOINTS ====================

@app.route('/api/admin/get-nodes', methods=['GET'])
def get_nodes():
    """Return all nodes with their chunk distribution data"""
    try:
        nodes_data = []
        for node_id, data in nodes_registry.items():
            nodes_data.append({
                'node_id': node_id,
                'chunk_count': data['chunk_count'],
                'file_count': len(data['files']),
                'files': data['files'],
                'active': data['active']
            })
        
        return jsonify({"nodes": nodes_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/add-node', methods=['POST'])
def add_node():
    """Add a new node to the system"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if not node_id:
            return jsonify({"error": "Node ID required"}), 400
        
        if node_id in nodes_registry:
            return jsonify({"error": "Node already exists"}), 400
        
        nodes_registry[node_id] = {
            'chunk_count': 0,
            'files': [],
            'active': True,
            'chunks': []
        }
        
        print(f"➕ New node added: {node_id}")
        return jsonify({"success": True, "message": f"Node {node_id} added"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/toggle-node', methods=['POST'])
def toggle_node():
    """Toggle node active status"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if node_id not in nodes_registry:
            return jsonify({"error": "Node not found"}), 404
        
        nodes_registry[node_id]['active'] = not nodes_registry[node_id]['active']
        status = "activated" if nodes_registry[node_id]['active'] else "deactivated"
        
        print(f"🔄 Node {node_id} {status}")
        return jsonify({"success": True, "active": nodes_registry[node_id]['active']}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/delete-node', methods=['POST'])
def delete_node():
    """Delete a node from the system"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if node_id not in nodes_registry:
            return jsonify({"error": "Node not found"}), 404
        
        del nodes_registry[node_id]
        print(f"🗑️ Node deleted: {node_id}")
        return jsonify({"success": True, "message": f"Node {node_id} deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "registered_users": len(users_registry),
            "pending_payments": len([r for r in payment_requests if r['status'] == 'pending']),
            "total_files": sum(len(files) for files in user_files.values()),
            "active_nodes": len([n for n in nodes_registry.values() if n['active']]),
            "total_chunks": sum(n['chunk_count'] for n in nodes_registry.values())
        }
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Flask API Gateway Started")
    print("=" * 60)
    print(f"📡 Server: http://localhost:5000")
    print(f"🔗 gRPC Backend: {GRPC_SERVER_ADDRESS}")
    print(f"📦 Chunk Distribution: ENABLED")
    print("=" * 60)
    app.run(port=5000, debug=True)