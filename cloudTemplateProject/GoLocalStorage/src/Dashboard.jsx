import React, { useState, useEffect, useRef } from 'react';
import { Cloud, LogOut, Upload, HardDrive, CreditCard, X, AlertCircle, Edit2, Trash2, Check } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5000';

const Dashboard = ({ username, onLogout }) => {
  const [storageInfo, setStorageInfo] = useState({
    used: 0,
    total: 2048, // 2GB in MB
    percentage: 0
  });
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showStorageWarning, setShowStorageWarning] = useState(false);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showQuotaExceededModal, setShowQuotaExceededModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [quotaExceededInfo, setQuotaExceededInfo] = useState({ 
    fileName: '',
    fileSize: 0, 
    available: 0 
  });
  const [editingFile, setEditingFile] = useState(null);
  const [newFileName, setNewFileName] = useState('');
  
  const [paymentDetails, setPaymentDetails] = useState({
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
    billingAddress: '',
    city: '',
    postalCode: '',
    country: 'Cameroon'
  });
  
  const fileInputRef = useRef(null);

  const plans = [
    { storage: 2, price: 20000, color: '#4caf50', popular: false },
    { storage: 3, price: 30000, color: '#2196f3', popular: true },
    { storage: 5, price: 50000, color: '#ff9800', popular: false }
  ];
  
  useEffect(() => {
    fetchStorageStatus();
    fetchUserFiles();
  }, [username]);

  useEffect(() => {
    if (storageInfo.percentage >= 80 && !showStorageWarning) {
      setShowStorageWarning(true);
    }
  }, [storageInfo.percentage, showStorageWarning]);

  const fetchStorageStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/get-user-quota/${username}`);

      const data = await response.json();
      if (response.ok && !data.error) {
        const used = data.used;
        const total = data.total;
        
        setStorageInfo({
          used,
          total,
          percentage: (used / total) * 100
        });

        if (showQuotaExceededModal && total > quotaExceededInfo.available) {
          setShowQuotaExceededModal(false);
        }

      } else {
        console.error('Failed to fetch storage status:', data.error || data.result);
      }
    } catch (error) {
      console.error('Failed to fetch storage status:', error);
    }
  };

  const fetchUserFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/get-user-files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });

      const data = await response.json();
      if (response.ok && data.files) {
        // Ensure files are sorted by timestamp (newest first)
        const sortedFiles = data.files.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setFiles(sortedFiles);
      } else {
         // Handle case where user might have no files
         setFiles([]);
      }
    } catch (error) {
      console.error('Failed to fetch files:', error);
      setFiles([]);
    }
  };

  /**
   * Generates a unique file name by appending (1), (2), etc.
   * if a file with the same name already exists in the current file list.
   * @param {string} fileName The original file name.
   * @returns {string} The unique file name.
   */
  const getUniqueFileName = (fileName) => {
    const fileNameParts = fileName.split('.');
    // Handle files without extensions
    const ext = fileNameParts.length > 1 ? `.${fileNameParts.pop()}` : '';
    const baseName = fileNameParts.join('.');
    
    let newName = fileName;
    let count = 0;
    
    // Check if the file name already exists
    while (files.some(f => f.name === newName)) {
      count++;
      newName = `${baseName} (${count})${ext}`;
    }
    
    return newName;
  };

  const getTimeAgo = (timestamp) => {
    const now = new Date();
    const uploadTime = new Date(timestamp);
    const diffMs = now - uploadTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const fileSizeMB = file.size / (1024 * 1024);
    const availableSpaceMB = storageInfo.total - storageInfo.used;
    
    if (fileSizeMB > availableSpaceMB) {
      setQuotaExceededInfo({
        fileName: file.name,
        fileSize: fileSizeMB,
        available: availableSpaceMB
      });
      setShowQuotaExceededModal(true);
      event.target.value = '';
      return;
    }

    // New Logic: Get a unique file name
    const uniqueFileName = getUniqueFileName(file.name);

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const response = await fetch(`${API_BASE_URL}/api/grpc-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'upload_file',
          params: {
            username,
            file_name: uniqueFileName, // Use the unique name
            file_size_mb: fileSizeMB
          }
        })
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      const data = await response.json();
      
      if (response.ok && data.type !== 'ERROR') {
        // Optimistic update, but fetchUserFiles is called shortly after for server truth
        const newFile = {
          // Use a unique ID based on the unique file name to prevent collision issues
          id: `${username}-${uniqueFileName}-${Date.now()}`,
          name: uniqueFileName,
          size: fileSizeMB.toFixed(2),
          timestamp: new Date().toISOString(),
          extension: uniqueFileName.split('.').pop().toUpperCase()
        };
        setFiles(prev => [newFile, ...prev]);
        
        setTimeout(async () => {
          // Fetch server data to ensure consistency and persistence
          await fetchStorageStatus();
          await fetchUserFiles();
          setIsUploading(false);
          setUploadProgress(0);
        }, 500);
      } else {
        alert(data.result || 'Upload failed');
        setIsUploading(false);
        setUploadProgress(0);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setIsUploading(false);
      setUploadProgress(0);
    }
    
    event.target.value = '';
  };

  const handleRenameFile = (fileId) => {
    const file = files.find(f => f.id === fileId);
    if (file) {
      setEditingFile(fileId);
      setNewFileName(file.name);
    }
  };

  // Modified: Now calls backend API for persistence and re-fetches files
  const saveFileRename = async () => {
    if (!newFileName.trim()) {
      alert('File name cannot be empty');
      return;
    }
    
    const fileToRename = files.find(f => f.id === editingFile);
    if (!fileToRename) return;

    // Use the unique naming helper for the new name as well
    const uniqueNewFileName = getUniqueFileName(newFileName);

    try {
        // ASSUMPTION: This endpoint must be implemented in web_client.py
        const response = await fetch(`${API_BASE_URL}/api/rename-file`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                file_id: editingFile,
                new_file_name: uniqueNewFileName
            })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            // Re-fetch the files list from the server to get the updated file list (persistence on refresh)
            await fetchUserFiles();
            
            setEditingFile(null);
            setNewFileName('');
            alert(`✅ File renamed to "${uniqueNewFileName}" successfully.`);
        } else {
            alert(data.error || 'Failed to rename file on server. Ensure /api/rename-file is implemented.');
        }
    } catch (error) {
        console.error('Rename error:', error);
        alert('An error occurred during file renaming.');
    }
  };

  // Modified: Now calls backend API for persistence and re-fetches files/storage
  const handleDeleteFile = async (fileId) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;

    if (!confirm(`Are you sure you want to delete "${file.name}"?`)) return;
    
    // Optimistic UI update for immediate feedback (will be overwritten by fetch)
    setFiles(prev => prev.filter(f => f.id !== fileId));

    try {
        // ASSUMPTION: This endpoint must be implemented in web_client.py
        const response = await fetch(`${API_BASE_URL}/api/delete-file`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                file_id: fileId, // Use unique file ID to delete the correct file
                file_size_mb: parseFloat(file.size)
            })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            // Re-fetch data to reflect server-side changes (guaranteed persistence and consistency)
            await fetchUserFiles();
            await fetchStorageStatus();
            alert(`✅ File "${file.name}" deleted successfully.`);
        } else {
            // Revert optimistic update if deletion fails
            await fetchUserFiles(); 
            alert(data.error || 'Failed to delete file on server. Ensure /api/delete-file is implemented.');
        }
    } catch (error) {
        console.error('Deletion error:', error);
        await fetchUserFiles(); // Revert on network error
        alert('An error occurred during file deletion.');
    }
  };

  const handleSelectPlan = (plan) => {
    setSelectedPlan(plan);
    setShowPurchaseModal(false);
    setShowPaymentModal(true);
  };

  const formatCardNumber = (value) => {
    const cleaned = value.replace(/\s/g, '');
    const matches = cleaned.match(/.{1,4}/g);
    return matches ? matches.join(' ') : cleaned;
  };

  const handleCardNumberChange = (value) => {
    const cleaned = value.replace(/\s/g, '');
    if (cleaned.length <= 16 && /^\d*$/.test(cleaned)) {
      setPaymentDetails({
        ...paymentDetails,
        cardNumber: formatCardNumber(cleaned)
      });
    }
  };

  const handleExpiryChange = (value) => {
    let cleaned = value.replace(/\D/g, '');
    if (cleaned.length >= 2) {
      cleaned = cleaned.slice(0, 2) + '/' + cleaned.slice(2, 4);
    }
    if (cleaned.length <= 5) {
      setPaymentDetails({ ...paymentDetails, expiryDate: cleaned });
    }
  };

  const handleCvvChange = (value) => {
    if (value.length <= 3 && /^\d*$/.test(value)) {
      setPaymentDetails({ ...paymentDetails, cvv: value });
    }
  };

  const handlePayment = async (e) => {
    e.preventDefault(); // Prevent default form submission

    // Validate payment details
    if (!paymentDetails.cardNumber || paymentDetails.cardNumber.replace(/\s/g, '').length !== 16) {
      alert('Please enter a valid 16-digit card number');
      return;
    }
    if (!paymentDetails.cardName.trim()) {
      alert('Please enter the cardholder name');
      return;
    }
    if (!paymentDetails.expiryDate || paymentDetails.expiryDate.length !== 5) {
      alert('Please enter expiry date (MM/YY)');
      return;
    }
    if (!paymentDetails.cvv || paymentDetails.cvv.length !== 3) {
      alert('Please enter a valid 3-digit CVV');
      return;
    }
    if (!paymentDetails.billingAddress.trim()) {
      alert('Please enter billing address');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/request-storage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          additional_storage_gb: selectedPlan.storage,
          price: selectedPlan.price,
          payment_details: paymentDetails
        })
      });

      const data = await response.json();
      if (response.ok) {
        alert(`✅ Payment request submitted successfully!\n\nYou've requested ${selectedPlan.storage}GB for ${selectedPlan.price.toLocaleString()} XAF.\n\nAn admin will approve your request shortly.`);
        setShowPaymentModal(false);
        setShowQuotaExceededModal(false);
        // Reset payment details
        setPaymentDetails({
          cardNumber: '',
          cardName: '',
          expiryDate: '',
          cvv: '',
          billingAddress: '',
          city: '',
          postalCode: '',
          country: 'Cameroon'
        });
      } else {
        alert(data.result || 'Payment request failed. Please check server logs.');
      }
    } catch (error) {
      console.error('Payment request failed:', error);
      alert('Failed to submit payment request. Please try again.');
    }
  };

  return (
    <>
      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        .dashboard-page {
          min-height: 100vh;
          background: #f5f5f5;
        }

        .dashboard-header {
          background: linear-gradient(135deg, #558b2f 0%, #689f38 100%);
          padding: 20px 40px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .header-left {
          display: flex;
          align-items: center;
          gap: 15px;
          color: white;
        }

        .header-brand {
          font-size: 28px;
          font-weight: 800;
        }

        .header-subtitle {
          font-size: 14px;
          opacity: 0.9;
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 20px;
          color: white;
        }

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

        .logout-btn:hover {
          background: rgba(255, 255, 255, 0.3);
        }

        .warning-banner {
          background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
          color: white;
          padding: 15px 40px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          animation: slideDown 0.5s ease;
        }

        @keyframes slideDown {
          from { transform: translateY(-100%); }
          to { transform: translateY(0); }
        }

        .warning-text {
          flex: 1;
          font-weight: 600;
        }

        .warning-btn {
          background: white;
          color: #f57c00;
          border: none;
          padding: 8px 20px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .warning-btn:hover {
          background: #f5f5f5;
        }

        .dashboard-content {
          padding: 40px;
          max-width: 1400px;
          margin: 0 auto;
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 30px;
          margin-bottom: 40px;
        }

        .storage-card, .upload-card {
          background: white;
          border-radius: 20px;
          padding: 30px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }

        .storage-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .storage-title {
          font-size: 24px;
          font-weight: 700;
          color: #1b5e20;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .storage-stats {
          font-size: 20px;
          color: #1b5e20;
          font-weight: 600;
        }

        .storage-bar-container {
          margin: 20px 0;
        }

        .storage-bar {
          width: 100%;
          height: 12px;
          background: #e0e0e0;
          border-radius: 6px;
          overflow: hidden;
        }

        .storage-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #558b2f 0%, #689f38 100%);
          transition: width 0.5s ease;
          border-radius: 6px;
        }

        .storage-bar-fill.warning {
          background: linear-gradient(90deg, #f57c00 0%, #ff9800 100%);
        }

        .storage-bar-fill.critical {
          background: linear-gradient(90deg, #d32f2f 0%, #f44336 100%);
        }

        .storage-details {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-top: 20px;
        }

        .storage-detail {
          background: #f5f5f5;
          padding: 20px;
          border-radius: 12px;
        }

        .storage-detail-label {
          font-size: 12px;
          color: #666;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        .storage-detail-value {
          font-size: 28px;
          font-weight: 700;
          color: #1b5e20;
        }

        .upload-card {
          text-align: center;
        }

        .upload-icon {
          width: 80px;
          height: 80px;
          background: #f1f8f4;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          color: #558b2f;
        }

        .upload-title {
          font-size: 20px;
          font-weight: 700;
          color: #1b5e20;
          margin-bottom: 10px;
        }

        .upload-description {
          color: #666;
          margin-bottom: 30px;
          font-size: 14px;
        }

        .upload-btn {
          background: linear-gradient(135deg, #558b2f 0%, #689f38 100%);
          color: white;
          border: none;
          padding: 15px 40px;
          border-radius: 12px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 10px;
          transition: all 0.3s ease;
        }

        .upload-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(85, 139, 47, 0.3);
        }

        .upload-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .files-section {
          background: white;
          border-radius: 20px;
          padding: 30px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }

        .files-header {
          font-size: 24px;
          font-weight: 700;
          color: #1b5e20;
          margin-bottom: 30px;
        }

        .no-files {
          text-align: center;
          padding: 60px 20px;
        }

        .no-files-icon {
          width: 80px;
          height: 80px;
          background: #f5f5f5;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          color: #bbb;
        }

        .no-files-title {
          font-size: 20px;
          font-weight: 600;
          color: #333;
          margin-bottom: 8px;
        }

        .no-files-text {
          color: #999;
        }

        .files-list {
          display: grid;
          gap: 12px;
        }

        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          background: #f9f9f9;
          border-radius: 12px;
          transition: all 0.3s ease;
        }

        .file-item:hover {
          background: #f1f8f4;
        }

        .file-info {
          display: flex;
          align-items: center;
          gap: 15px;
          flex: 1;
        }

        .file-icon {
          width: 45px;
          height: 45px;
          background: linear-gradient(135deg, #558b2f 0%, #689f38 100%);
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 10px;
          font-weight: 700;
        }

        .file-details {
          flex: 1;
        }

        .file-details h4 {
          font-size: 15px;
          font-weight: 600;
          color: #333;
          margin-bottom: 6px;
        }

        .file-edit-input {
          padding: 6px 10px;
          border: 2px solid #4caf50;
          border-radius: 6px;
          font-size: 15px;
          font-weight: 600;
          width: 300px;
        }

        .file-meta {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: #999;
        }

        .file-meta span {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .file-actions {
          display: flex;
          gap: 8px;
        }

        .file-action-btn {
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

        .file-action-btn.rename {
          background: #e3f2fd;
          color: #2196f3;
        }

        .file-action-btn.delete {
          background: #ffebee;
          color: #f44336;
        }

        .file-action-btn.save {
          background: #e8f5e9;
          color: #4caf50;
        }

        .file-action-btn:hover {
          transform: scale(1.1);
        }

        .progress-overlay {
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

        .progress-card {
          background: white;
          border-radius: 16px;
          padding: 40px;
          text-align: center;
          min-width: 300px;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #e0e0e0;
          border-radius: 4px;
          overflow: hidden;
          margin: 20px 0;
        }

        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #558b2f 0%, #689f38 100%);
          transition: width 0.3s ease;
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
          padding: 20px;
        }

        .modal-content {
          background: white;
          border-radius: 20px;
          padding: 40px;
          max-width: 600px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
        }

        .modal-close {
          position: absolute;
          top: 20px;
          right: 20px;
          background: #f5f5f5;
          border: none;
          width: 35px;
          height: 35px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        .modal-close:hover {
          background: #e0e0e0;
        }

        .modal-title {
          font-size: 28px;
          font-weight: 700;
          color: #1b5e20;
          margin-bottom: 15px;
          text-align: center;
        }

        .modal-subtitle {
          color: #666;
          margin-bottom: 30px;
          text-align: center;
          line-height: 1.6;
        }

        .quota-exceeded-icon {
          width: 80px;
          height: 80px;
          background: #ffebee;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          color: #f44336;
        }

        .quota-info {
          background: #f5f5f5;
          padding: 20px;
          border-radius: 12px;
          margin: 20px 0;
        }

        .quota-info-row {
          display: flex;
          justify-content: space-between;
          padding: 10px 0;
          border-bottom: 1px solid #e0e0e0;
          font-size: 15px;
        }

        .quota-info-row:last-child {
          border-bottom: none;
        }

        .quota-info-row strong {
          color: #333;
        }

        .quota-info-row.highlight {
          color: #f44336;
          font-weight: 600;
        }

        .modal-actions {
          display: flex;
          gap: 15px;
          margin-top: 25px;
        }

        .btn-secondary {
          flex: 1;
          padding: 12px;
          background: #f5f5f5;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .btn-secondary:hover {
          background: #e0e0e0;
        }

        .btn-primary {
          flex: 1;
          padding: 12px;
          background: linear-gradient(135deg, #558b2f 0%, #689f38 100%);
          color: white;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 15px rgba(85, 139, 47, 0.3);
        }

        .plans-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
          margin-bottom: 30px;
        }

        .plan-card {
          border: 3px solid #e0e0e0;
          border-radius: 16px;
          padding: 25px 20px;
          text-align: center;
          cursor: pointer;
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
        }

        .plan-card.popular {
          border-color: #2196f3;
          transform: scale(1.05);
        }

        .plan-card:hover {
          transform: translateY(-5px) scale(1.02);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }

        .plan-card.popular:hover {
          transform: translateY(-5px) scale(1.07);
        }

        .popular-badge {
          position: absolute;
          top: 10px;
          right: 10px;
          background: #2196f3;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 700;
        }

        .plan-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: var(--plan-color);
        }

        .plan-storage {
          font-size: 36px;
          font-weight: 800;
          margin-bottom: 8px;
          color: var(--plan-color);
        }

        .plan-price {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 15px;
          color: #333;
        }

        .plan-btn {
          background: white;
          border: 2px solid var(--plan-color);
          color: var(--plan-color);
          padding: 10px 20px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          width: 100%;
        }

        .plan-btn:hover {
          background: var(--plan-color);
          color: white;
        }

        .payment-form {
          display: grid;
          gap: 20px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
        }

        .form-group label {
          font-size: 14px;
          font-weight: 600;
          color: #333;
          margin-bottom: 5px;
        }

        .form-group input, .form-group select {
          padding: 12px;
          border: 1px solid #ccc;
          border-radius: 8px;
          font-size: 16px;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        
        .pay-btn {
          background: linear-gradient(135deg, #4caf50 0%, #689f38 100%);
          color: white;
          border: none;
          padding: 15px 40px;
          border-radius: 12px;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          transition: all 0.3s ease;
          margin-top: 20px;
        }

        .pay-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
        }

        @media (max-width: 1024px) {
          .dashboard-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 600px) {
          .dashboard-header {
            padding: 15px 20px;
          }
          .header-brand {
            font-size: 24px;
          }
          .dashboard-content {
            padding: 20px;
          }
          .plans-grid {
            grid-template-columns: 1fr;
          }
          .file-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
          }
          .file-info {
            width: 100%;
          }
          .file-actions {
            width: 100%;
            justify-content: flex-end;
          }
          .form-row {
            grid-template-columns: 1fr;
          }
          .modal-content {
            padding: 25px;
          }
        }
      `}</style>

      <div className="dashboard-page">
        <header className="dashboard-header">
          <div className="header-left">
            <Cloud size={30} />
            <div className="header-text">
              <div className="header-brand">GoLocal Storage</div>
              <div className="header-subtitle">Welcome back, {username}</div>
            </div>
          </div>
          <div className="header-right">
            <button className="logout-btn" onClick={onLogout}>
              <LogOut size={20} />
              Logout
            </button>
          </div>
        </header>

        {showStorageWarning && (
          <div className="warning-banner">
            <AlertCircle size={24} style={{ marginRight: '15px' }} />
            <div className="warning-text">
              You're running low on storage! You have used {storageInfo.percentage.toFixed(1)}% of your quota. Consider upgrading your plan to avoid interruption.
            </div>
            <button className="warning-btn" onClick={() => {
              setShowStorageWarning(false);
              setShowPurchaseModal(true);
            }}>
              Upgrade Now
            </button>
          </div>
        )}

        <main className="dashboard-content">
          <div className="dashboard-grid">
            <div className="storage-card">
              <div className="storage-header">
                <h2 className="storage-title">
                  <HardDrive size={24} /> Storage Overview
                </h2>
                <div className="storage-stats">
                  {storageInfo.used.toFixed(2)} MB / {(storageInfo.total / 1024).toFixed(2)} GB
                </div>
              </div>
              <div className="storage-bar-container">
                <div className="storage-bar">
                  <div
                    className={`storage-bar-fill ${storageInfo.percentage >= 95 ? 'critical' : storageInfo.percentage >= 80 ? 'warning' : ''}`}
                    style={{ width: `${storageInfo.percentage.toFixed(2)}%` }}
                  ></div>
                </div>
              </div>
              <div className="storage-details">
                <div className="storage-detail">
                  <div className="storage-detail-label">Used Space</div>
                  <div className="storage-detail-value">{storageInfo.used.toFixed(2)} MB</div>
                </div>
                <div className="storage-detail">
                  <div className="storage-detail-label">Total Quota</div>
                  <div className="storage-detail-value">{(storageInfo.total / 1024).toFixed(2)} GB</div>
                </div>
              </div>
              <button
                className="upload-btn"
                style={{ width: '100%', marginTop: '30px' }}
                onClick={() => setShowPurchaseModal(true)}
              >
                <CreditCard size={20} /> Upgrade Storage
              </button>
            </div>
            
            <div className="upload-card">
              <div className="upload-icon">
                <Upload size={40} />
              </div>
              <h3 className="upload-title">Secure File Upload</h3>
              <p className="upload-description">
                Upload your files securely. All data is encrypted using 2-factor authentication.
              </p>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                style={{ display: 'none' }}
                disabled={isUploading}
              />
              <button 
                className="upload-btn" 
                onClick={() => fileInputRef.current.click()}
                disabled={isUploading}
              >
                <Upload size={20} /> {isUploading ? 'Uploading...' : 'Choose File to Upload'}
              </button>
            </div>
          </div>

          <div className="files-section">
            <h2 className="files-header">My Files ({files.length})</h2>
            {files.length === 0 ? (
              <div className="no-files">
                <div className="no-files-icon">
                  <Cloud size={40} />
                </div>
                <div className="no-files-title">No files uploaded yet</div>
                <div className="no-files-text">Click the upload button to start securing your files.</div>
              </div>
            ) : (
              <div className="files-list">
                {files.map(file => (
                  <div key={file.id} className="file-item">
                    <div className="file-info">
                      <div className="file-icon">{file.extension}</div>
                      <div className="file-details">
                        {editingFile === file.id ? (
                          <input
                            type="text"
                            className="file-edit-input"
                            value={newFileName}
                            onChange={(e) => setNewFileName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && saveFileRename()}
                          />
                        ) : (
                          <h4>{file.name}</h4>
                        )}
                        <div className="file-meta">
                          <span>Size: {file.size} MB</span>
                          <span>Uploaded: {getTimeAgo(file.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="file-actions">
                      {editingFile === file.id ? (
                        <button className="file-action-btn save" onClick={saveFileRename}>
                          <Check size={20} />
                        </button>
                      ) : (
                        <button className="file-action-btn rename" onClick={() => handleRenameFile(file.id)}>
                          <Edit2 size={20} />
                        </button>
                      )}
                      <button className="file-action-btn delete" onClick={() => handleDeleteFile(file.id)}>
                        <Trash2 size={20} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        {/* Upload Progress Modal */}
        {isUploading && (
          <div className="progress-overlay">
            <div className="progress-card">
              <h3>Uploading File...</h3>
              <p style={{ color: '#666', margin: '10px 0' }}>{uploadProgress}% Complete</p>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p style={{ fontSize: '12px', color: '#999' }}>Please wait while your file is securely uploaded.</p>
            </div>
          </div>
        )}

        {/* Purchase Modal */}
        {showPurchaseModal && (
          <div className="modal">
            <div className="modal-content">
              <button className="modal-close" onClick={() => setShowPurchaseModal(false)}>
                <X size={20} />
              </button>
              <h2 className="modal-title">Upgrade Your Storage</h2>
              <p className="modal-subtitle">
                Select a plan to instantly increase your total cloud storage quota.
              </p>

              <div className="plans-grid">
                {plans.map(plan => (
                  <div 
                    key={plan.storage}
                    className={`plan-card ${plan.popular ? 'popular' : ''}`}
                    style={{ '--plan-color': plan.color }}
                  >
                    {plan.popular && <span className="popular-badge">POPULAR</span>}
                    <HardDrive size={40} style={{ color: plan.color, marginBottom: '10px' }} />
                    <div className="plan-storage">{plan.storage} GB</div>
                    <div className="plan-price">{plan.price.toLocaleString()} XAF</div>
                    <button 
                      className="plan-btn"
                      style={{ '--plan-color': plan.color }}
                      onClick={() => handleSelectPlan(plan)}
                    >
                      Select Plan
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Quota Exceeded Modal */}
        {showQuotaExceededModal && (
          <div className="modal">
            <div className="modal-content">
              <button className="modal-close" onClick={() => setShowQuotaExceededModal(false)}>
                <X size={20} />
              </button>
              <div className="quota-exceeded-icon">
                <AlertCircle size={40} />
              </div>
              <h2 className="modal-title" style={{ color: '#f44336' }}>Storage Quota Exceeded</h2>
              <p className="modal-subtitle">
                Your file **{quotaExceededInfo.fileName}** ({quotaExceededInfo.fileSize.toFixed(2)} MB) is too large for your remaining space.
              </p>

              <div className="quota-info">
                <div className="quota-info-row">
                  <span>File Size:</span>
                  <strong>{quotaExceededInfo.fileSize.toFixed(2)} MB</strong>
                </div>
                <div className="quota-info-row highlight">
                  <span>Available Space:</span>
                  <strong>{quotaExceededInfo.available.toFixed(2)} MB</strong>
                </div>
              </div>

              <p className="modal-subtitle" style={{ marginBottom: '0' }}>
                Please upgrade your plan to upload this file and continue using GoLocal Storage.
              </p>

              <div className="modal-actions">
                <button 
                  className="btn-secondary" 
                  onClick={() => setShowQuotaExceededModal(false)}
                >
                  Cancel
                </button>
                <button 
                  className="btn-primary"
                  onClick={() => {
                    setShowQuotaExceededModal(false);
                    setShowPurchaseModal(true);
                  }}
                >
                  <CreditCard size={20} /> Upgrade Storage
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Payment Modal */}
        {showPaymentModal && selectedPlan && (
          <div className="modal">
            <div className="modal-content">
              <button className="modal-close" onClick={() => setShowPaymentModal(false)}>
                <X size={20} />
              </button>
              <h2 className="modal-title">Complete Purchase</h2>
              <p className="modal-subtitle">
                You are purchasing **{selectedPlan.storage} GB** of extra storage for **{selectedPlan.price.toLocaleString()} XAF**.
              </p>

              <form className="payment-form" onSubmit={handlePayment}>
                <div className="form-group">
                  <label>Card Number</label>
                  <input
                    type="text"
                    placeholder="XXXX XXXX XXXX XXXX"
                    value={paymentDetails.cardNumber}
                    onChange={(e) => handleCardNumberChange(e.target.value)}
                    maxLength="19"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Cardholder Name</label>
                  <input
                    type="text"
                    placeholder="John Doe"
                    value={paymentDetails.cardName}
                    onChange={(e) => setPaymentDetails({...paymentDetails, cardName: e.target.value})}
                    required
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Expiry Date (MM/YY)</label>
                    <input
                      type="text"
                      placeholder="MM/YY"
                      value={paymentDetails.expiryDate}
                      onChange={(e) => handleExpiryChange(e.target.value)}
                      maxLength="5"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>CVV</label>
                    <input
                      type="text"
                      placeholder="XXX"
                      value={paymentDetails.cvv}
                      onChange={(e) => handleCvvChange(e.target.value)}
                      maxLength="3"
                      required
                    />
                  </div>
                </div>

                <h3 className="modal-title" style={{ marginTop: '20px', marginBottom: '0', fontSize: '20px' }}>Billing Address</h3>

                <div className="form-group">
                  <label>Address</label>
                  <input
                    type="text"
                    placeholder="123 Main St"
                    value={paymentDetails.billingAddress}
                    onChange={(e) => setPaymentDetails({...paymentDetails, billingAddress: e.target.value})}
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>City</label>
                    <input
                      type="text"
                      placeholder="Yaounde"
                      value={paymentDetails.city}
                      onChange={(e) => setPaymentDetails({...paymentDetails, city: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Postal Code</label>
                    <input
                      type="text"
                      placeholder="00000"
                      value={paymentDetails.postalCode}
                      onChange={(e) => setPaymentDetails({...paymentDetails, postalCode: e.target.value})}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Country</label>
                  <select
                    value={paymentDetails.country}
                    onChange={(e) => setPaymentDetails({...paymentDetails, country: e.target.value})}
                  >
                    <option>Cameroon</option>
                    <option>Chad</option>
                    <option>Central African Republic</option>
                    <option>Gabon</option>
                    <option>Equatorial Guinea</option>
                    <option>Republic of the Congo</option>
                  </select>
                </div>

                <button type="submit" className="pay-btn">
                  <CreditCard size={20} />
                  Pay {selectedPlan.price.toLocaleString()} XAF
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default Dashboard;