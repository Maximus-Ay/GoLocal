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
users_registry = {}  # Store user info for admin dashboard

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
                
                # Register user in our local registry
                if response and "success" in response.result.lower():
                    users_registry[params['username']] = {
                        'username': params['username'],
                        'email': params['email'],
                        'used_quota_gb': 0.0,
                        'total_quota_gb': 2.0,  # Default 2GB quota
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
            # NOTE: We keep this for gRPC purposes, but the user quota will be fetched
            # from the new /api/get-user-quota endpoint for local consistency.
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
                
                # Store file info
                username = params['username']
                if username not in user_files:
                    user_files[username] = []
                
                file_name = params['file_name']
                file_extension = file_name.split('.')[-1].upper() if '.' in file_name else 'FILE'

                # Use the unique file name (guaranteed by frontend) as the file ID for consistency
                user_files[username].append({
                    'id': file_name,
                    'name': file_name,
                    'size': f"{file_size_mb:.2f}",
                    'timestamp': datetime.now().isoformat(),
                    'extension': file_extension
                })
                
                # Update user's used quota
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
        
        # Returns files which now contain the 'id' field
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
        # file_id is the original unique file name used as the identifier
        old_file_id = data.get('file_id') 
        new_file_name = data.get('new_file_name')
        
        if not all([username, old_file_id, new_file_name]):
            return jsonify({"error": "Missing parameters (username, file_id, new_file_name)"}), 400

        if username not in user_files:
            return jsonify({"error": "User has no files"}), 404
        
        # Find and rename the file
        found = False
        for file in user_files[username]:
            if file['id'] == old_file_id:
                # Update the file object with the new name and re-generate the ID/Extension
                file['name'] = new_file_name
                file['id'] = new_file_name 
                file['extension'] = new_file_name.split('.')[-1].upper() if '.' in new_file_name else 'FILE'
                
                # TODO: In production, you would call gRPC here to rename the file
                
                found = True
                break
        
        if found:
            print(f"🔄 File renamed: {old_file_id} -> {new_file_name} for user {username}")
            return jsonify({"success": True, "message": f"File renamed to {new_file_name}"}), 200
        else:
            return jsonify({"error": f"File with ID {old_file_id} not found"}), 404
    except Exception as e:
        print(f"❌ Error in rename_file: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    try:
        data = request.get_json()
        username = data.get('username')
        # file_id is the unique file name
        file_id = data.get('file_id') 
        file_size_mb = data.get('file_size_mb') # Used to update quota
        
        if not all([username, file_id, file_size_mb is not None]):
            return jsonify({"error": "Missing parameters (username, file_id, file_size_mb)"}), 400

        if username not in user_files:
            return jsonify({"error": "User has no files"}), 404
        
        initial_file_count = len(user_files[username])
        
        # Filter out the file to delete (matching by the unique ID)
        user_files[username] = [file for file in user_files[username] if file['id'] != file_id]
        
        deleted_count = initial_file_count - len(user_files[username])
        
        if deleted_count > 0:
            # Update user's used quota
            if username in users_registry:
                quota_to_reduce = file_size_mb / 1024
                # Ensure used quota does not go below zero
                users_registry[username]['used_quota_gb'] = max(0, users_registry[username]['used_quota_gb'] - quota_to_reduce)
            
            # TODO: In production, you would call gRPC here to delete the file
            
            print(f"🗑️ File deleted: {file_id} for user {username}. Quota reduced by {file_size_mb:.2f} MB.")
            return jsonify({"success": True, "message": f"File {file_id} deleted successfully"}), 200
        else:
            return jsonify({"error": f"File with ID {file_id} not found"}), 404
    except Exception as e:
        print(f"❌ Error in delete_file: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ==================== STORAGE REQUEST ENDPOINT (FIXED) ====================

@app.route('/api/request-storage', methods=['POST'])
def request_storage():
    """
    Handles the request for additional storage from the Dashboard.jsx frontend.
    Stores the request in the in-memory payment_requests list for admin approval.
    """
    try:
        data = request.get_json()
        username = data.get('username')
        additional_storage_gb = data.get('additional_storage_gb')
        price = data.get('price')
        payment_details = data.get('payment_details')
        
        if not all([username, additional_storage_gb, price, payment_details]):
            return jsonify({"result": "Missing required fields for storage request"}), 400

        # Create a unique ID for the request (simple timestamp-based for now)
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
        
        print(f"💳 New storage request received from {username}. ID: {request_id}")
        
        return jsonify({"result": "Payment request submitted successfully for admin approval", "request_id": request_id}), 200

    except Exception as e:
        print(f"❌ Error in request_storage: {str(e)}")
        return jsonify({"result": "Internal server error during request submission.", "error": str(e)}), 500

# ==================== USER QUOTA ENDPOINT ====================

@app.route('/api/get-user-quota/<username>', methods=['GET'])
def get_user_quota(username):
    """
    Returns a user's current storage quota directly from the local users_registry,
    which is updated by the admin approval process. Returns sizes in MB.
    """
    try:
        user = users_registry.get(username)
        if user:
            # Convert GB values in registry to MB for the Dashboard frontend
            quota_mb = {
                'used': round(user['used_quota_gb'] * 1024, 2), 
                'total': user['total_quota_gb'] * 1024          
            }
            return jsonify(quota_mb), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"❌ Error in get_user_quota: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/get-users', methods=['GET'])
def get_users():
    try:
        # Return all registered users
        users_list = list(users_registry.values())
        
        # If no users in registry, return sample data for testing
        if not users_list:
            users_list = [
                {
                    "username": "demo_user",
                    "email": "demo@example.com",
                    "used_quota_gb": 0.5,
                    "total_quota_gb": 2.0
                }
            ]
        
        print(f"📊 Admin requested users list: {len(users_list)} users")
        return jsonify({"users": users_list}), 200
    except Exception as e:
        print(f"❌ Error in get_users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/get-payment-requests', methods=['GET'])
def get_payment_requests():
    try:
        # Return only pending payment requests
        pending = [req for req in payment_requests if req['status'] == 'pending']
        
        print(f"💳 Admin requested payment requests: {len(pending)} pending")
        return jsonify({"requests": pending}), 200
    except Exception as e:
        print(f"❌ Error in get_payment_requests: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/approve-payment', methods=['POST'])
def approve_payment():
    try:
        data = request.get_json()
        username = data.get('username')
        storage_gb = data.get('additional_storage_gb')
        
        print(f"✅ Admin approving payment for {username}: +{storage_gb}GB")
        
        # Update payment request status
        for req in payment_requests:
            if req['username'] == username and req['status'] == 'pending':
                req['status'] = 'approved'
                break
        
        # Update user's total quota
        if username in users_registry:
            users_registry[username]['total_quota_gb'] += storage_gb
            print(f"   New total quota for {username}: {users_registry[username]['total_quota_gb']}GB")
        else:
            print(f"⚠️  Warning: User {username} not found in registry")
        
        # TODO: In production, you would call the gRPC server here to update the actual quota:
        # stub = get_grpc_stub()
        # response = stub.increase_quota(cloudsecurity_pb2.QuotaRequest(
        #     login=username,
        #     additional_storage_gb=storage_gb
        # ))
        
        return jsonify({"result": "Payment approved successfully"}), 200
    except Exception as e:
        print(f"❌ Error in approve_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/reject-payment', methods=['POST'])
def reject_payment():
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        
        print(f"❌ Admin rejecting payment request ID: {request_id}")
        
        # Update payment request status
        for req in payment_requests:
            if req['id'] == request_id:
                req['status'] = 'rejected'
                print(f"   Rejected request for user: {req['username']}")
                break
        
        return jsonify({"result": "Payment rejected"}), 200
    except Exception as e:
        print(f"❌ Error in reject_payment: {str(e)}")
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
            "total_files": sum(len(files) for files in user_files.values())
        }
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Flask API Gateway Started")
    print("=" * 60)
    print(f"📡 Server: http://localhost:5000")
    print(f"🔗 gRPC Backend: {GRPC_SERVER_ADDRESS}")
    print(f"📋 Available Endpoints:")
    print(f"   - POST /api/grpc-call")
    print(f"   - POST /api/request-storage    <- FIXED")
    print(f"   - POST /api/rename-file")
    print(f"   - POST /api/delete-file")
    print(f"   - POST /api/get-user-files")
    print(f"   - GET  /api/get-user-quota/<username>")
    print(f"   - GET  /api/admin/get-users")
    print(f"   - GET  /api/admin/get-payment-requests")
    print(f"   - POST /api/admin/approve-payment")
    print(f"   - POST /api/admin/reject-payment")
    print(f"   - GET  /api/health")
    print("=" * 60)
    app.run(port=5000, debug=True)