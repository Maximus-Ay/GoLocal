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
                
                user_files[username].append({
                    'name': params['file_name'],
                    'size': f"{file_size_mb:.2f}",
                    'timestamp': datetime.now().isoformat(),
                    'extension': params['file_name'].split('.')[-1].upper() if '.' in params['file_name'] else 'FILE'
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
        
        files = user_files.get(username, [])
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/request-storage', methods=['POST', 'OPTIONS'])
def request_storage():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        storage_gb = data.get('additional_storage_gb')
        price = data.get('price')
        
        # Create a unique request ID
        request_id = len(payment_requests) + 1
        
        payment_requests.append({
            'id': request_id,
            'username': username,
            'storage_gb': storage_gb,
            'price': price,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        })
        
        print(f"✅ Payment request received: {username} wants {storage_gb}GB for {price} XAF")
        
        return jsonify({"result": "Request submitted successfully"}), 200
    except Exception as e:
        print(f"❌ Error in request_storage: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ==================== USER QUOTA ENDPOINT (NEW) ====================

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
    print(f"   - POST /api/request-storage")
    print(f"   - GET  /api/get-user-quota/<username> (NEW)") # Added new route to console log
    print(f"   - GET  /api/admin/get-users")
    print(f"   - GET  /api/admin/get-payment-requests")
    print(f"   - POST /api/admin/approve-payment")
    print(f"   - POST /api/admin/reject-payment")
    print(f"   - GET  /api/health")
    print("=" * 60)
    app.run(port=5000, debug=True)