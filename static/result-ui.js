(function(){
	const gauges = document.querySelectorAll('.gauge');
	const CIRCUMFERENCE = 2 * Math.PI * 54; // r=54
	gauges.forEach(g => {
		const pct = Math.max(0, Math.min(100, parseInt(g.getAttribute('data-percentage') || '0', 10)));
		const progress = g.querySelector('.gauge-progress');
		if(progress){
			const offset = CIRCUMFERENCE * (1 - pct / 100);
			progress.style.strokeDasharray = String(CIRCUMFERENCE);
			progress.style.strokeDashoffset = String(CIRCUMFERENCE);
			requestAnimationFrame(()=>{
				progress.style.strokeDashoffset = String(offset);
			});
		}
	});
})(); 