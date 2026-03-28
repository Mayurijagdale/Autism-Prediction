(function(){
	const startBtn = document.getElementById('startCamBtn');
	const stopBtn = document.getElementById('stopCamBtn');
	const captureBtn = document.getElementById('captureBtn');
	const video = document.getElementById('liveVideo');
	const canvas = document.getElementById('snapshotCanvas');
	const hiddenInput = document.getElementById('cameraImageData');
	let stream = null;

	async function startCamera(){
		try{
			stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
			video.srcObject = stream;
		}catch(err){
			alert('Unable to access camera: ' + err.message);
		}
	}

	function stopCamera(){
		if(stream){
			stream.getTracks().forEach(t => t.stop());
			stream = null;
			video.srcObject = null;
		}
	}

	function captureSnapshot(){
		if(!stream){
			alert('Start the camera first.');
			return;
		}
		const ctx = canvas.getContext('2d');
		canvas.width = video.videoWidth || 640;
		canvas.height = video.videoHeight || 480;
		ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
		const dataUrl = canvas.toDataURL('image/jpeg');
		hiddenInput.value = dataUrl;
		canvas.hidden = false;
	}

	if(startBtn){ startBtn.addEventListener('click', startCamera); }
	if(stopBtn){ stopBtn.addEventListener('click', stopCamera); }
	if(captureBtn){ captureBtn.addEventListener('click', captureSnapshot); }

	window.addEventListener('beforeunload', stopCamera);
})(); 