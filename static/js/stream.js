const chips = document.querySelectorAll('.video-chip');
const startBtn = document.getElementById('start-btn');
const playerFrame = document.getElementById('player-frame');
const placeholder = document.getElementById('placeholder');
const liveTag = document.getElementById('live-tag');

let selectedVideo = null;

chips.forEach(chip => {
  chip.addEventListener('click', () => {
    chips.forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    selectedVideo = chip.dataset.video;
    startBtn.disabled = false;
  });
});

startBtn.addEventListener('click', async () => {
  if (!selectedVideo) return;
  startBtn.disabled = true;
  startBtn.textContent = 'Mengirim perintah START…';

  try {
    const res = await fetch('/api/start_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video: selectedVideo })
    });
    const data = await res.json();

    if (data.status === 'success') {
      if (placeholder) placeholder.remove();
      // Bust cache tiap kali start supaya img tag reconnect ke /video_feed
      const img = document.createElement('img');
      img.src = '/video_feed?_=' + Date.now();
      playerFrame.appendChild(img);
      liveTag.classList.add('on');
      startBtn.textContent = 'Streaming berjalan';
    } else {
      startBtn.textContent = 'Gagal: ' + data.message;
      startBtn.disabled = false;
    }
  } catch (e) {
    startBtn.textContent = 'Gagal terhubung ke server';
    startBtn.disabled = false;
  }
});
