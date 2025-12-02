// Função principal para buscar dados e desenhar os gráficos
async function carregarDashboard() {
    // Acessa as variáveis globais definidas no template HTML
    const gameId = window.gameId;
    const gameName = window.gameName;

    // Verificação CORRIGIDA: Apenas checa se a variável é nula, indefinida ou a string "None"
    if (!gameId || typeof gameId === 'undefined' || gameId === 'None') {
        console.error('Erro: gameId não foi definido corretamente no template HTML.');
        return;
    }

    try {
        // Agora o FETCH será executado corretamente:
        const apiUrl = `/api/analises/${gameId}`;
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            // Exibe mensagem de erro na seção de análise
            exibirMensagemErro(gameName, `HTTP error! status: ${response.status} ao acessar ${apiUrl}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 2. CONVERTER A RESPOSTA PARA JSON
        const dados = await response.json();

        // 3. CHAMA AS FUNÇÕES PARA DESENHAR OS GRÁFICOS ou exibe mensagem
        if (dados.labels && dados.labels.length > 0) {
            desenharGraficoAvaliacoes(dados);
            desenharGraficoVisualizadores(dados);
        } else {
            exibirMensagemSemDados(gameName);
        }

    } catch (error) {
        console.error('Erro ao carregar o dashboard:', error);
        // Exibe uma mensagem de erro na página
        exibirMensagemErro(gameName, `Não foi possível conectar ao servidor. Detalhes: ${error.message}`);
    }
}

// Função auxiliar para exibir mensagem de erro na seção do dashboard
function exibirMensagemErro(gameName, mensagem) {
    const twitchAnalysisSection = document.querySelector('.twitch-analysis');
    if (twitchAnalysisSection) {
        twitchAnalysisSection.innerHTML = `
            <div class="text-center p-8 bg-red-100 rounded-lg border border-red-400">
                <h2 class="text-3xl font-bold mb-4 text-gray-800">Streams Ativas na Twitch</h2>
                <p class="text-lg text-red-800">Erro ao carregar os dados de análise para **${gameName}**.</p>
                <p class="text-sm text-red-700 mt-2">Detalhes: ${mensagem}</p>
            </div>
        `;
    }
}

// Função auxiliar para exibir mensagem quando não há streams ativas
function exibirMensagemSemDados(gameName) {
    const twitchAnalysisSection = document.querySelector('.twitch-analysis');
    if (twitchAnalysisSection) {
        twitchAnalysisSection.innerHTML = `
            <div class="text-center p-8 bg-yellow-100 rounded-lg border border-yellow-400">
                <h2 class="text-3xl font-bold mb-4 text-gray-800">Streams Ativas na Twitch</h2>
                <p class="text-lg text-yellow-800">Não encontramos streams ativas para **${gameName}** no momento.</p>
                <p class="text-sm text-yellow-700 mt-2">Os gráficos serão exibidos assim que as transmissões forem iniciadas.</p>
            </div>
        `;
    }
}

// Função para desenhar o gráfico de Avaliação Simulada
function desenharGraficoAvaliacoes(dados) {
    // Usa 'avaliacaoChart' (ID do HTML)
    const ctxAvaliacoes = document.getElementById('avaliacaoChart')?.getContext('2d'); 

    if (!ctxAvaliacoes) return; 

    new Chart(ctxAvaliacoes, {
        type: 'doughnut', // Gráfico de Rosca
        data: {
            labels: dados.labels,
            datasets: [{
                label: 'Média de Avaliação Simulada (1 a 5)',
                data: dados.data_avaliacoes,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'],
                borderColor: '#ffffff',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                title: {
                    display: true,
                    text: 'Avaliação Simulada por Stream' 
                }
            }
        }
    });
}

// Função para desenhar o gráfico de Visualizadores Reais
function desenharGraficoVisualizadores(dados) {
    // Usa 'visualizadorChart' (ID do HTML)
    const ctxVisualizadores = document.getElementById('visualizadorChart')?.getContext('2d'); 

    if (!ctxVisualizadores) return; 

    new Chart(ctxVisualizadores, {
        type: 'bar', // Gráfico de Barras
        data: {
            labels: dados.labels,
            datasets: [{
                label: 'Visualizadores Atuais (Twitch API)',
                data: dados.data_visualizadores,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Contagem de Visualizadores' }
                }
            },
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Visualizadores por Stream Ativa' 
                }
            }
        }
    });
}

// Chama a função principal ao carregar a página
window.onload = carregarDashboard;