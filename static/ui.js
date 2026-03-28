(function(){
	const html = document.documentElement;
	const btn = document.getElementById('themeToggle');
	const key = 'prefers-dark';
	function applyTheme(v){
		if(v === '1') html.classList.add('dark'); else html.classList.remove('dark');
	}
	let pref = localStorage.getItem(key) || '0';
	applyTheme(pref);
	if(btn){
		btn.addEventListener('click', function(){
			pref = pref === '1' ? '0' : '1';
			localStorage.setItem(key, pref);
			applyTheme(pref);
		});
	}
})(); 