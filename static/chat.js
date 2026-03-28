(function(){
	const chatForm = document.getElementById('chatForm');
	const input = document.getElementById('chatMessage');
	const sendBtn = document.getElementById('chatSendBtn');
	const windowEl = document.getElementById('chatWindow');

	function append(role, text){
		const div = document.createElement('div');
		div.className = 'message ' + role;
		div.textContent = text;
		windowEl.appendChild(div);
		windowEl.scrollTop = windowEl.scrollHeight;
	}

	async function sendMessage(){
		const text = (input.value || '').trim();
		if(!text) return;
		append('user', text);
		input.value = '';
		sendBtn.disabled = true;
		try{
			const res = await fetch('/chat_message', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: text })
			});
			if(!res.ok){
				append('assistant', 'Sorry, there was an error.');
				return;
			}
			const data = await res.json();
			append('assistant', data.reply || '');
		}catch(err){
			append('assistant', 'Error: ' + err.message);
		}finally{
			sendBtn.disabled = false;
			input.focus();
		}
	}

	if(chatForm){
		chatForm.addEventListener('submit', sendMessage);
		input.addEventListener('keydown', function(e){
			if(e.key === 'Enter' && !e.shiftKey){
				e.preventDefault();
				sendMessage();
			}
		});
	}
})(); 