(function(){
	const form = document.getElementById('assessmentForm');
	const progress = document.getElementById('progressBar');
	if(!form || !progress) return;

	const inputs = Array.from(form.querySelectorAll('input[type=range], input[type=file], input[type=hidden]'));
	function updateBadge(range){
		const wrapper = range.parentElement;
		if(!wrapper) return;
		const badge = wrapper.querySelector('.badge');
		if(badge) badge.textContent = String(range.value);
	}
	inputs.forEach(el => {
		if(el.type === 'range'){
			updateBadge(el);
			el.addEventListener('input', () => updateBadge(el));
		}
	});

	function calcProgress(){
		// Count range inputs as always filled; optional image fields count when non-empty
		const ranges = Array.from(form.querySelectorAll('input[type=range]'));
		const total = ranges.length + 2; // include optional photo and camera snapshot
		let done = ranges.length;
		const photo = form.querySelector('input[type=file]');
		if(photo && photo.files && photo.files.length > 0) done += 1;
		const camera = form.querySelector('input#cameraFilename');
		if(camera && camera.value) done += 1;
		const pct = Math.min(100, Math.round((done / total) * 100));
		progress.style.width = pct + '%';
	}
	calcProgress();
	form.addEventListener('input', calcProgress);
})(); 