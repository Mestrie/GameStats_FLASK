// Função utilitária para Debounce (atrasar a execução de uma função)
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('pesquisa');
    const suggestionsList = document.getElementById('suggestions-list');
    const form = document.getElementById('search-form');

    // Função para esconder a lista quando o usuário clicar fora
    document.addEventListener('click', (e) => {
        if (e.target.id !== 'pesquisa' && e.target.closest('#suggestions-list') === null) {
            suggestionsList.classList.add('hidden');
        }
    });

    const fetchSuggestions = debounce(async (query) => {
        if (query.length < 3) {
            suggestionsList.innerHTML = '';
            suggestionsList.classList.add('hidden');
            return;
        }

        try {
            // Chama o endpoint de API do Flask
            const response = await fetch(`/api/sugestoes?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Falha ao buscar sugestões');

            const suggestions = await response.json();
            renderSuggestions(suggestions);

        } catch (error) {
            console.error("Erro no fetch de sugestões:", error);
            suggestionsList.innerHTML = '<li class="p-3 text-red-500">Erro ao carregar.</li>';
            suggestionsList.classList.remove('hidden');
        }
    }, 300); // 300ms de atraso para evitar muitas chamadas à API

    function renderSuggestions(suggestions) {
        suggestionsList.innerHTML = '';
        
        if (suggestions.length === 0) {
            suggestionsList.innerHTML = '<li class="p-3 text-gray-500">Nenhum resultado encontrado.</li>';
            suggestionsList.classList.remove('hidden');
            return;
        }

        suggestions.forEach(item => {
            const li = document.createElement('li');
            li.className = 'p-3 cursor-pointer hover:bg-blue-50 transition duration-150 truncate';
            li.textContent = item.name;
            
            // CRUCIAL: Ao clicar na sugestão, preenche o campo e submete o formulário
            li.addEventListener('click', () => {
                input.value = item.name;
                suggestionsList.classList.add('hidden');
                form.submit(); // Submete o formulário para ir para a página de listagem
            });

            suggestionsList.appendChild(li);
        });

        suggestionsList.classList.remove('hidden');
    }

    input.addEventListener('input', (e) => {
        fetchSuggestions(e.target.value.trim());
    });
    
    // Garante que a lista apareça quando o usuário volta ao campo
    input.addEventListener('focus', (e) => {
         if (e.target.value.length >= 3) {
            suggestionsList.classList.remove('hidden');
         }
    });
});