const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const dzFilename = document.getElementById('dz-filename');
const uploadBtn = document.getElementById('upload-btn');
const form = document.getElementById('upload-form');
const progressWrap = document.getElementById('progress-wrap');
const progressFill = document.getElementById('progress-fill');
const progressLabel = document.getElementById('progress-label');

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) {
    dzFilename.textContent = fileInput.files[0].name;
    uploadBtn.disabled = false;
  }
});

['dragover', 'dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.toggle('drag', evt === 'dragover');
  });
});
dropzone.addEventListener('drop', (e) => {
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    dzFilename.textContent = fileInput.files[0].name;
    uploadBtn.disabled = false;
  }
});

form.addEventListener('submit', (e) => {
  e.preventDefault();
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload');

  progressWrap.style.display = 'block';
  uploadBtn.disabled = true;
  uploadBtn.textContent = 'Mengirim via TCP…';

  xhr.upload.addEventListener('progress', (evt) => {
    if (evt.lengthComputable) {
      const pct = Math.round((evt.loaded / evt.total) * 100);
      progressFill.style.width = pct + '%';
      progressLabel.textContent = pct + '%';
    }
  });

  xhr.onload = () => {
    let data = {};
    try { data = JSON.parse(xhr.responseText); } catch (e) {}
    if (xhr.status === 200 && data.status === 'success') {
      progressLabel.textContent = 'Berhasil — menyimpan via TCP server';
      setTimeout(() => window.location.reload(), 600);
    } else {
      progressLabel.textContent = 'Gagal: ' + (data.message || 'terjadi kesalahan');
      uploadBtn.disabled = false;
      uploadBtn.textContent = 'Coba lagi';
    }
  };
  xhr.onerror = () => {
    progressLabel.textContent = 'Gagal terhubung ke server.';
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Coba lagi';
  };

  xhr.send(formData);
});
