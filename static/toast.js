(function(){
	const container = document.getElementById('toastContainer');
	function ensure(){ return container; }
	function makeToast(message, type){
		const el = document.createElement('div');
		el.className = 'toast' + (type ? ' ' + type : '');
		el.textContent = message;
		ensure().appendChild(el);
		setTimeout(()=>{ el.style.opacity = '0'; }, 2600);
		setTimeout(()=>{ el.remove(); }, 3000);
	}
	window.showToast = makeToast;
})(); 