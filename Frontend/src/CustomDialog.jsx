import React from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';

const CustomDialog = ({ 
  isOpen, 
  onClose, 
  title, 
  message, 
  type = 'info', // 'success', 'error', 'warning', 'info', 'confirm'
  onConfirm,
  confirmText = 'OK',
  cancelText = 'Cancel',
  showCancel = false
}) => {
  if (!isOpen) return null;

  const getIcon = () => {
    switch(type) {
      case 'success':
        return <CheckCircle size={48} color="#4caf50" />;
      case 'error':
        return <XCircle size={48} color="#f44336" />;
      case 'warning':
        return <AlertCircle size={48} color="#ff9800" />;
      case 'confirm':
        return <AlertCircle size={48} color="#2196f3" />;
      default:
        return <Info size={48} color="#2196f3" />;
    }
  };

  const getColor = () => {
    switch(type) {
      case 'success': return '#4caf50';
      case 'error': return '#f44336';
      case 'warning': return '#ff9800';
      case 'confirm': return '#2196f3';
      default: return '#2196f3';
    }
  };

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
    onClose();
  };

  return (
    <>
      <style>{`
        .dialog-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideUp {
          from { 
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        .dialog-content {
          background: white;
          border-radius: 20px;
          padding: 40px;
          max-width: 450px;
          width: 90%;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          animation: slideUp 0.3s ease;
          position: relative;
        }

        .dialog-close-btn {
          position: absolute;
          top: 15px;
          right: 15px;
          background: #f5f5f5;
          border: none;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          color: #666;
        }

        .dialog-close-btn:hover {
          background: #e0e0e0;
          transform: rotate(90deg);
        }

        .dialog-icon-container {
          display: flex;
          justify-content: center;
          margin-bottom: 20px;
        }

        .dialog-title {
          font-size: 24px;
          font-weight: 700;
          color: #333;
          text-align: center;
          margin-bottom: 15px;
        }

        .dialog-message {
          color: #666;
          text-align: center;
          line-height: 1.6;
          margin-bottom: 30px;
          font-size: 15px;
        }

        .dialog-buttons {
          display: flex;
          gap: 12px;
          justify-content: center;
        }

        .dialog-btn {
          padding: 12px 30px;
          border: none;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          min-width: 100px;
        }

        .dialog-btn-confirm {
          background: var(--dialog-color);
          color: white;
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        .dialog-btn-confirm:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }

        .dialog-btn-cancel {
          background: #f5f5f5;
          color: #666;
        }

        .dialog-btn-cancel:hover {
          background: #e0e0e0;
        }
      `}</style>

      <div className="dialog-overlay" onClick={onClose}>
        <div 
          className="dialog-content" 
          onClick={(e) => e.stopPropagation()}
          style={{ '--dialog-color': getColor() }}
        >
          <button className="dialog-close-btn" onClick={onClose}>
            <X size={18} />
          </button>

          <div className="dialog-icon-container">
            {getIcon()}
          </div>

          <h2 className="dialog-title">{title}</h2>
          <p className="dialog-message">{message}</p>

          <div className="dialog-buttons">
            {showCancel && (
              <button className="dialog-btn dialog-btn-cancel" onClick={onClose}>
                {cancelText}
              </button>
            )}
            <button className="dialog-btn dialog-btn-confirm" onClick={handleConfirm}>
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default CustomDialog;