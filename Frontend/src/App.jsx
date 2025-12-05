import React, { useState, useEffect } from 'react';
import { Lock, Cloud } from 'lucide-react';
import Dashboard from './Dashboard';
import AdminDashboard from './AdminDashboard';

const API_BASE_URL = 'http://localhost:5000';

// ==================== SHARED COMPONENTS ====================
const InputField = ({ id, type, placeholder, value, onChange, disabled = false, error = '' }) => (
  <div className="input-group">
    <input
      id={id}
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={`form-input ${error ? 'error' : ''}`}
    />
    {error && <span className="error-message">{error}</span>}
  </div>
);

const Button = ({ onClick, disabled, loading, children, variant = 'primary' }) => (
  <button
    onClick={onClick}
    disabled={disabled || loading}
    className={`btn btn-${variant} ${loading ? 'loading' : ''}`}
  >
    {loading ? (
      <>
        <div className="spinner"></div>
        Processing...
      </>
    ) : children}
  </button>
);

const StatusAlert = ({ message, type }) => {
  if (!message) return null;
  return (
    <div className={`alert alert-${type}`}>
      {message}
    </div>
  );
};

// ==================== SIGNUP COMPONENT ====================
const Signup = ({ onSuccess, onSwitchToLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [status, setStatus] = useState({ message: '', type: '' });
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = () => {
    const newErrors = {};
    if (!username.trim()) newErrors.username = 'Username is required';
    if (!email.trim()) newErrors.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(email)) newErrors.email = 'Email is invalid';
    if (!password) newErrors.password = 'Password is required';
    else if (password.length < 6) newErrors.password = 'Password must be at least 6 characters';
    if (password !== confirmPassword) newErrors.confirmPassword = 'Passwords do not match';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSignup = async () => {
    if (!validateForm()) {
      setStatus({ message: 'Please fix the errors above', type: 'error' });
      return;
    }

    setIsLoading(true);
    setStatus({ message: '', type: '' });

    try {
      const response = await fetch(`${API_BASE_URL}/api/grpc-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'signup',
          params: { username, email, password }
        })
      });

      const data = await response.json();

      if (response.ok && data.type !== 'ERROR') {
        setStatus({ message: 'Account created! OTP sent to your email.', type: 'success' });
        setTimeout(() => onSuccess(username), 1500);
      } else {
        setStatus({ message: data.result || 'Signup failed', type: 'error' });
      }
    } catch (error) {
      setStatus({ message: 'Network error. Please check your connection.', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="app-title">
        <Cloud size={32} />
        <h1>GoLocal Storage</h1>
      </div>
      <div className="auth-header">
        <h2>Create Account</h2>
        <p>Join GoLocal Cloud Storage today</p>
      </div>

      <StatusAlert message={status.message} type={status.type} />

      <div className="auth-form">
        <InputField
          id="signup-username"
          type="text"
          placeholder="Username"
          value={username}
          onChange={setUsername}
          disabled={isLoading}
          error={errors.username}
        />
        <InputField
          id="signup-email"
          type="email"
          placeholder="Email Address"
          value={email}
          onChange={setEmail}
          disabled={isLoading}
          error={errors.email}
        />
        <InputField
          id="signup-password"
          type="password"
          placeholder="Password"
          value={password}
          onChange={setPassword}
          disabled={isLoading}
          error={errors.password}
        />
        <InputField
          id="signup-confirm"
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={setConfirmPassword}
          disabled={isLoading}
          error={errors.confirmPassword}
        />
        <Button onClick={handleSignup} loading={isLoading} variant="primary">
          Create Account
        </Button>
        <div className="auth-footer">
          Already have an account?{' '}
          <button onClick={onSwitchToLogin} className="link-button">
            Log In
          </button>
        </div>
      </div>
    </div>
  );
};

// ==================== LOGIN COMPONENT ====================
const Login = ({ onSuccess, onSwitchToSignup }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [status, setStatus] = useState({ message: '', type: '' });
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = () => {
    const newErrors = {};
    if (!username.trim()) newErrors.username = 'Username is required';
    if (!password) newErrors.password = 'Password is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    if (!validateForm()) {
      setStatus({ message: 'Please fill in all fields', type: 'error' });
      return;
    }

    setIsLoading(true);
    setStatus({ message: '', type: '' });

    try {
      const response = await fetch(`${API_BASE_URL}/api/grpc-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'login',
          params: { username, password }
        })
      });

      const data = await response.json();

      if (response.ok && data.type !== 'ERROR') {
        setStatus({ message: 'Login successful! OTP sent to your email.', type: 'success' });
        setTimeout(() => onSuccess(username), 1500);
      } else {
        setStatus({ message: data.result || 'Login failed', type: 'error' });
      }
    } catch (error) {
      setStatus({ message: 'Network error. Please check your connection.', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="app-title">
        <Cloud size={32} />
        <h1>GoLocal Storage</h1>
      </div>
      <div className="auth-header">
        <h2>Welcome Back</h2>
        <p>Log in to access your cloud storage</p>
      </div>
      <StatusAlert message={status.message} type={status.type} />
      <div className="auth-form">
        <InputField
          id="login-username"
          type="text"
          placeholder="Username"
          value={username}
          onChange={setUsername}
          disabled={isLoading}
          error={errors.username}
        />
        <InputField
          id="login-password"
          type="password"
          placeholder="Password"
          value={password}
          onChange={setPassword}
          disabled={isLoading}
          error={errors.password}
        />
        <Button onClick={handleLogin} loading={isLoading} variant="primary">
          Log In
        </Button>
        
        <div className="auth-footer">
          Don't have an account?{' '}
          <button onClick={onSwitchToSignup} className="link-button">
            Sign Up
          </button>
        </div>
      </div>
    </div>
  );
};

// ==================== OTP VERIFICATION ====================
const OtpVerification = ({ username, onSuccess, onBack }) => {
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (index, value) => {
    if (value.length > 1) value = value[0];
    if (!/^\d*$/.test(value)) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    
    if (value && index < 5) {
      document.getElementById(`otp-${index + 1}`)?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      document.getElementById(`otp-${index - 1}`)?.focus();
    }
  };

  const handleVerifyOtp = async () => {
    const otpCode = otp.join('');
    if (otpCode.length !== 6) {
      setStatus({ message: 'Please enter all 6 digits', type: 'error' });
      return;
    }

    setIsLoading(true);
    setStatus({ message: '', type: '' });

    try {
      const response = await fetch(`${API_BASE_URL}/api/grpc-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'verify_otp',
          params: { username, otp: otpCode }
        })
      });

      const data = await response.json();

      if (response.ok && data.session_token) {
        localStorage.setItem('sessionToken', data.session_token);
        localStorage.setItem('username', username);
        // Check if user is admin (username is "Admin" case-insensitive)
        const isAdmin = username.toLowerCase() === 'admin';
        localStorage.setItem('userRole', isAdmin ? 'admin' : 'user');
        setStatus({ message: 'Verification successful!', type: 'success' });
        setTimeout(() => onSuccess(isAdmin), 1000);
      } else {
        setStatus({ message: data.result || 'Invalid OTP', type: 'error' });
      }
    } catch (error) {
      setStatus({ message: 'Network error. Please try again.', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container otp-auth-container">
      <div className="app-title">
        <div className="otp-icon-large">
          <Lock size={36} />
        </div>
        <h1>GoLocal Storage</h1>
      </div>
      
      <div className="auth-header">
        <h2>Verify Your Identity</h2>
        <p>Enter the 6-digit code sent to your registered email</p>
      </div>

      <StatusAlert message={status.message} type={status.type} />
      
      <div className="otp-inputs">
        {otp.map((digit, index) => (
          <input
            key={index}
            id={`otp-${index}`}
            type="text"
            maxLength="1"
            value={digit}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            className="otp-box"
            disabled={isLoading}
          />
        ))}
      </div>
      
      <Button 
        onClick={handleVerifyOtp} 
        loading={isLoading} 
        variant="primary"
      >
        Verify
      </Button>
      
      <p className="otp-demo-text">Check your email for the OTP code</p>
      
      <button onClick={onBack} className="otp-back-button">
        ← Back to Login
      </button>
    </div>
  );
};

// ==================== MAIN APP ====================
const App = () => {
  const [view, setView] = useState('login');
  const [username, setUsername] = useState('');
  const [userRole, setUserRole] = useState('user');

  useEffect(() => {
    const token = localStorage.getItem('sessionToken');
    const savedUsername = localStorage.getItem('username');
    const savedRole = localStorage.getItem('userRole') || 'user';
    if (token && savedUsername) {
      setUsername(savedUsername);
      setUserRole(savedRole);
      setView(savedRole === 'admin' ? 'admin-dashboard' : 'dashboard');
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('username');
    localStorage.removeItem('userRole');
    setUsername('');
    setUserRole('user');
    setView('login');
  };

  return (
    <>
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
          min-height: 100vh;
        }

        .app {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        /* App Title */
        .app-title {
          text-align: center;
          margin-bottom: 30px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 15px;
        }

        .app-title svg {
          color: #2e7d32;
        }

        .app-title h1 {
          color: #1b5e20;
          font-size: 32px;
          font-weight: 800;
        }

        .otp-icon-large {
          width: 70px;
          height: 70px;
          background: linear-gradient(135deg, #558b2f 0%, #689f38 100%);
          border-radius: 18px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        /* Auth Container */
        .auth-container {
          background: white;
          border-radius: 20px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
          padding: 40px;
          width: 100%;
          max-width: 450px;
          animation: fadeIn 0.5s ease;
        }

        .otp-auth-container {
          max-width: 500px;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .auth-header {
          text-align: center;
          margin-bottom: 30px;
        }

        .auth-header h2 {
          color: #2e7d32;
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 8px;
        }

        .auth-header p {
          color: #666;
          font-size: 14px;
        }

        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .auth-footer {
          text-align: center;
          color: #666;
          font-size: 14px;
          margin-top: 10px;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .form-input {
          width: 100%;
          padding: 15px;
          border: 2px solid #e0e0e0;
          border-radius: 12px;
          font-size: 15px;
          transition: all 0.3s ease;
        }

        .form-input:focus {
          outline: none;
          border-color: #4caf50;
          box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
        }

        .form-input.error {
          border-color: #f44336;
        }

        .error-message {
          color: #f44336;
          font-size: 12px;
        }

        .btn {
          padding: 15px 24px;
          border: none;
          border-radius: 12px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .btn-primary {
          background: linear-gradient(135deg, #689f38 0%, #558b2f 100%);
          color: white;
          box-shadow: 0 4px 15px rgba(104, 159, 56, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(104, 159, 56, 0.4);
        }

        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .link-button {
          background: none;
          border: none;
          color: #689f38;
          font-weight: 600;
          cursor: pointer;
        }

        .link-button:hover {
          text-decoration: underline;
        }

        .spinner {
          width: 18px;
          height: 18px;
          border: 3px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .alert {
          padding: 14px 18px;
          border-radius: 12px;
          margin-bottom: 20px;
          font-size: 14px;
        }

        .alert-success {
          background: #e8f5e9;
          color: #2e7d32;
          border: 1px solid #81c784;
        }

        .alert-error {
          background: #ffebee;
          color: #c62828;
          border: 1px solid #ef9a9a;
        }

        /* OTP Inputs */
        .otp-inputs {
          display: flex;
          gap: 10px;
          justify-content: center;
          margin: 30px 0;
        }

        .otp-box {
          width: 55px;
          height: 55px;
          border: 2px solid #e0e0e0;
          border-radius: 12px;
          font-size: 24px;
          font-weight: 700;
          text-align: center;
          transition: all 0.3s ease;
          background: #f9f9f9;
        }

        .otp-box:focus {
          outline: none;
          border-color: #689f38;
          background: white;
          box-shadow: 0 0 0 3px rgba(104, 159, 56, 0.1);
        }

        .otp-demo-text {
          color: #999;
          font-size: 13px;
          text-align: center;
          margin-top: 15px;
        }

        .otp-back-button {
          background: none;
          border: none;
          color: #558b2f;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          margin-top: 20px;
          display: block;
          width: 100%;
          text-align: center;
        }

        .otp-back-button:hover {
          text-decoration: underline;
        }

        @media (max-width: 600px) {
          .auth-container {
            padding: 30px 20px;
          }
          
          .otp-box {
            width: 45px;
            height: 45px;
            font-size: 20px;
          }
          
          .otp-inputs {
            gap: 8px;
          }
        }
      `}</style>

      <div className="app">
        {view === 'login' && (
          <Login
            onSuccess={(user) => {
              setUsername(user);
              setView('otp');
            }}
            onSwitchToSignup={() => setView('signup')}
          />
        )}

        {view === 'signup' && (
          <Signup
            onSuccess={(user) => {
              setUsername(user);
              setView('otp');
            }}
            onSwitchToLogin={() => setView('login')}
          />
        )}

        {view === 'otp' && (
          <OtpVerification
            username={username}
            onSuccess={(isAdmin) => {
              setUserRole(isAdmin ? 'admin' : 'user');
              setView(isAdmin ? 'admin-dashboard' : 'dashboard');
            }}
            onBack={() => setView('login')}
          />
        )}

        {view === 'dashboard' && (
          <Dashboard username={username} onLogout={handleLogout} />
        )}

        {view === 'admin-dashboard' && (
          <AdminDashboard username={username} onLogout={handleLogout} />
        )}
      </div>
    </>
  );
};

export default App;