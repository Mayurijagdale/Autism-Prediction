(function(){
	const captureBtn = document.getElementById('captureOcvBtn');
	const hiddenFilename = document.getElementById('cameraFilename');
	if(!captureBtn) return;

	async function capture(){
		captureBtn.disabled = true;
		try{
			const res = await fetch('/capture', { method: 'POST' });
			if(!res.ok){
				const text = await res.text();
				alert('Capture failed: ' + text);
				return;
			}
			const data = await res.json();
			if(data && data.filename){
				hiddenFilename.value = data.filename;
				alert('Snapshot saved. It will be included in your submission.');
			}
		}catch(err){
			alert('Error: ' + err.message);
		}finally{
			captureBtn.disabled = false;
		}
	}

	captureBtn.addEventListener('click', capture);
})(); 