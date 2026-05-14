// Helper để fix encoding tiếng Việt
function fixVietnamese(str) {
  if (!str) return '';
  
  // Nếu đã có dấu tiếng Việt đúng, trả về nguyên
  if (/[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]/.test(str)) {
    return str;
  }
  
  // Thử các cách decode khác nhau
  try {
    // Cách 1: decodeURIComponent + escape
    try {
      const decoded = decodeURIComponent(escape(str));
      if (decoded !== str) return decoded;
    } catch (e) {}
    
    // Cách 2: TextDecoder với UTF-8
    try {
      const bytes = new Uint8Array(str.split('').map(c => c.charCodeAt(0)));
      const decoded = new TextDecoder('utf-8').decode(bytes);
      if (/[àáảãạăâđêôơư]/.test(decoded)) return decoded;
    } catch (e) {}
  } catch (e) {}
  
  return str;
}

// ---- Document bank ----
async function loadDocumentBank() {
  console.log('DEBUG: loadDocumentBank called');
  const container = document.getElementById('document-bank-container');
  console.log('DEBUG: Container element:', container);
  
  if (!container) {
    console.error('DEBUG: Container not found!');
    return;
  }
  
  // Hiển thị loading
  container.innerHTML = '<div style="text-align:center; padding:40px; color:#6b7280;">Đang tải...</div>';
  
  try {
    const res = await fetch(`${API}/documents`);
    console.log('DEBUG: API response status:', res.status);
    
    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }
    
    const documents = await res.json();
    console.log('DEBUG: Documents received:', documents);
    console.log('DEBUG: Documents count:', documents ? documents.length : 'null/undefined');
    
    if (!documents || !Array.isArray(documents) || documents.length === 0) {
      container.innerHTML = `
        <div class="empty" style="text-align:center; padding:40px;">
          <div style="font-size:48px; margin-bottom:16px;">📚</div>
          <div style="font-size:16px; font-weight:500; color:#e5e7eb; margin-bottom:8px;">Chưa có tài liệu nào</div>
          <div style="font-size:13px; color:#6b7280;">Tải file lên để bắt đầu xây dựng ngân hàng tài liệu</div>
        </div>`;
      return;
    }
    
    container.innerHTML = `
      <div class="history-list">
        ${documents.map(doc => `
          <div class="history-item" onclick="selectDocument('${doc.doc_id}', '${fixVietnamese(doc.filename)}')">
            <div class="history-icon">${doc.file_type === 'pdf' ? '📄' : doc.file_type === 'docx' ? '📝' : '📃'}</div>
            <div class="history-info">
              <div class="history-name">${fixVietnamese(doc.filename)}</div>
              <div class="history-meta">
                <span>${doc.file_type.toUpperCase()}</span>
                <span>${doc.num_chunks} đoạn</span>
                <span>${new Date(doc.created_at).toLocaleDateString('vi-VN')}</span>
              </div>
            </div>
            <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteDocument('${doc.doc_id}')">✕</button>
          </div>
        `).join('')}
      </div>`;
  } catch (err) {
    console.error('DEBUG: Lỗi tải tài liệu:', err);
    container.innerHTML = `
      <div style="text-align:center; padding:40px; color:#ef4444;">
        <div style="font-size:24px; margin-bottom:8px;">⚠️</div>
        <div style="font-size:14px;">Lỗi tải tài liệu</div>
        <div style="font-size:12px; color:#6b7280; margin-top:8px;">${err.message}</div>
      </div>`;
    toast('Lỗi tải tài liệu', 'error');
  }
}

function selectDocument(docId, filename) {
  state.docId = docId;
  toast(`Đã chọn tài liệu: ${filename}`, 'success');
  
  // Show preview
  const icon = filename.includes('.pdf') ? '📄' : filename.includes('.docx') ? '📝' : '📃';
  document.getElementById('file-preview-area').innerHTML = `
    <div class="file-preview">
      <div class="file-preview-icon">${icon}</div>
      <div class="file-preview-name">${filename}</div>
      <div class="file-preview-size">Đã tải lên</div>
      <button class="file-remove" onclick="removeFile()" title="Xóa file">✕</button>
    </div>`;
  
  // Switch back to file tab to show preview
  switchInputTab('file');
}

async function deleteDocument(docId) {
  if (!confirm('Xác nhận xóa tài liệu này?')) return;
  
  try {
    const res = await fetch(`${API}/documents/${docId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Lỗi xóa tài liệu');
    
    toast('Đã xóa tài liệu', 'success');
    loadDocumentBank(); // Refresh list
    
    // Clear selection if this was the selected document
    if (state.docId === docId) {
      removeFile();
    }
  } catch (err) {
    toast('Lỗi xóa tài liệu', 'error');
  }
}
