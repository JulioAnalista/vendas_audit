// Dashboard de Vendas - JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // ----- Variáveis Globais -----
    let chartVendas = null;
    let chartNCM = null;
    let chartMensal = null;
    
    // Período atual selecionado
    let periodoAtual = 'mes';
    
    // Dados para comparação
    let dadosAnteriores = {
        total_nfes: 0,
        valor_total: 0,
        ticket_medio: 0,
        total_produtos: 0
    };
    
    // ----- Funções de Formatação -----
    
    // Formata valores monetários
    function formatarMoeda(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }
    
    // Formata números com separadores de milhar
    function formatarNumero(valor) {
        return new Intl.NumberFormat('pt-BR').format(valor);
    }
    
    // Formata a variação percentual (positiva ou negativa)
    function formatarVariacao(atual, anterior) {
        if (anterior === 0) return { valor: 0, texto: '0%', classe: 'text-muted' };
        
        const variacao = ((atual - anterior) / anterior) * 100;
        const icone = variacao >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        const classe = variacao >= 0 ? 'text-success' : 'text-danger';
        
        return {
            valor: variacao,
            texto: `<i class="fas ${icone}"></i> ${Math.abs(variacao).toFixed(1)}%`,
            classe: classe
        };
    }
    
    // Atualiza o título da página baseado no tipo de operação
    function atualizarTitulos(tipoOperacao) {
        const operacao = tipoOperacao === 'saida' ? 'Vendas' : 'Compras';
        document.title = `Dashboard de ${operacao}`;
        
        // Verificar se o elemento existe antes de tentar atualizá-lo
        const h1Element = document.querySelector('.navbar-brand');
        if (h1Element) {
            h1Element.innerHTML = `<i class="fas fa-chart-bar me-2"></i>Dashboard de ${operacao}`;
        }
        
        // Atualizar títulos dos cards
        document.querySelectorAll('.card-title').forEach(el => {
            if (el.textContent.includes('Vendas')) {
                el.textContent = el.textContent.replace('Vendas', operacao);
            }
            if (el.textContent.includes('Vendidos')) {
                el.textContent = el.textContent.replace('Vendidos', tipoOperacao === 'saida' ? 'Vendidos' : 'Comprados');
            }
        });
    }
    
    // ----- Funções de Carregamento de Dados -----
    
    // Carrega dados do dashboard
    async function carregarDadosDashboard() {
        try {
            console.log("Iniciando carregamento de dados...");
            
            // Salvar dados atuais para comparação
            const totalNFEsAtual = parseFloat(document.getElementById('total-nfes').textContent.replace(/\D/g, ''));
            const valorTotalAtual = parseFloat(document.getElementById('total-valor').textContent.replace(/\D/g, '')) / 100;
            const ticketMedioAtual = parseFloat(document.getElementById('ticket-medio').textContent.replace(/\D/g, '')) / 100;
            const totalProdutosAtual = parseFloat(document.getElementById('total-produtos').textContent.replace(/\D/g, ''));
            
            if (!isNaN(totalNFEsAtual)) dadosAnteriores.total_nfes = totalNFEsAtual;
            if (!isNaN(valorTotalAtual)) dadosAnteriores.valor_total = valorTotalAtual;
            if (!isNaN(ticketMedioAtual)) dadosAnteriores.ticket_medio = ticketMedioAtual;
            if (!isNaN(totalProdutosAtual)) dadosAnteriores.total_produtos = totalProdutosAtual;
            
            // Buscar novos dados
            console.log(`Solicitando dados do dashboard para o período: ${periodoAtual}`);
            const resposta = await fetch(`/api/vendas/dashboard?periodo=${periodoAtual}`);
            if (!resposta.ok) {
                console.error(`Erro HTTP: ${resposta.status} ${resposta.statusText}`);
                throw new Error('Falha ao carregar dados do dashboard');
            }
            
            const dados = await resposta.json();
            console.log("Dados do dashboard recebidos:", dados);
            
            // Atualizar títulos baseado no tipo de operação
            atualizarTitulos(dados.tipo_operacao);
            
            // Atualizar indicadores
            atualizarIndicadores(dados);
            
            // Atualizar gráfico de vendas
            atualizarGraficoVendas(dados);
            
            // Buscar dados de produtos mais vendidos
            console.log("Solicitando dados de produtos mais vendidos...");
            const respostaProdutos = await fetch(`/api/produtos/mais-vendidos?periodo=${periodoAtual}&limite=10`);
            if (!respostaProdutos.ok) {
                console.error(`Erro HTTP (produtos): ${respostaProdutos.status} ${respostaProdutos.statusText}`);
                throw new Error('Falha ao carregar dados de produtos');
            }
            
            const dadosProdutos = await respostaProdutos.json();
            console.log("Dados de produtos recebidos:", dadosProdutos);
            atualizarTabelaProdutos(dadosProdutos.produtos);
            
            // Total de produtos
            const totalProdutos = dadosProdutos.produtos.reduce((total, produto) => total + produto.quantidade, 0);
            
            // Atualizar indicador de produtos e variação
            document.getElementById('total-produtos').textContent = formatarNumero(totalProdutos);
            const variacaoProdutos = formatarVariacao(totalProdutos, dadosAnteriores.total_produtos);
            document.getElementById('variacao-produtos').className = variacaoProdutos.classe;
            document.getElementById('variacao-produtos').innerHTML = variacaoProdutos.texto;
            
            // Buscar dados por NCM
            console.log("Solicitando dados por NCM...");
            const respostaNCM = await fetch(`/api/produtos/por-categoria?periodo=${periodoAtual}`);
            if (!respostaNCM.ok) {
                console.error(`Erro HTTP (NCM): ${respostaNCM.status} ${respostaNCM.statusText}`);
                throw new Error('Falha ao carregar dados por NCM');
            }
            
            const dadosNCM = await respostaNCM.json();
            console.log("Dados de NCM recebidos:", dadosNCM);
            atualizarGraficoNCM(dadosNCM.produtos);
            
            // Buscar dados mensais para o ano atual
            console.log("Solicitando dados mensais...");
            const anoAtual = new Date().getFullYear();
            const respostaMensal = await fetch(`/api/vendas/por-periodo?ano=${anoAtual}`);
            if (!respostaMensal.ok) {
                console.error(`Erro HTTP (mensal): ${respostaMensal.status} ${respostaMensal.statusText}`);
                throw new Error('Falha ao carregar dados mensais');
            }
            
            const dadosMensal = await respostaMensal.json();
            console.log("Dados mensais recebidos:", dadosMensal);
            atualizarGraficoMensal(dadosMensal.vendas);
            
            console.log("Carregamento de dados concluído com sucesso!");
        } catch (erro) {
            console.error('Erro ao carregar dados:', erro);
            exibirMensagemErro(`Erro ao carregar dados: ${erro.message}`);
        }
    }
    
    // ----- Funções de Atualização da Interface -----
    
    // Atualiza os indicadores principais
    function atualizarIndicadores(dados) {
        // Atualizar total de NFes
        document.getElementById('total-nfes').textContent = formatarNumero(dados.total_nfes);
        const variacaoNFEs = formatarVariacao(dados.total_nfes, dadosAnteriores.total_nfes);
        document.getElementById('variacao-nfes').className = variacaoNFEs.classe;
        document.getElementById('variacao-nfes').innerHTML = variacaoNFEs.texto;
        
        // Atualizar valor total
        document.getElementById('total-valor').textContent = formatarMoeda(dados.valor_total);
        const variacaoValor = formatarVariacao(dados.valor_total, dadosAnteriores.valor_total);
        document.getElementById('variacao-valor').className = variacaoValor.classe;
        document.getElementById('variacao-valor').innerHTML = variacaoValor.texto;
        
        // Calcular e atualizar ticket médio
        const ticketMedio = dados.total_nfes > 0 ? dados.valor_total / dados.total_nfes : 0;
        document.getElementById('ticket-medio').textContent = formatarMoeda(ticketMedio);
        const variacaoTicket = formatarVariacao(ticketMedio, dadosAnteriores.ticket_medio);
        document.getElementById('variacao-ticket').className = variacaoTicket.classe;
        document.getElementById('variacao-ticket').innerHTML = variacaoTicket.texto;
    }
    
    // Atualiza a tabela de produtos mais vendidos
    function atualizarTabelaProdutos(produtos) {
        console.log("Atualizando tabela de produtos com", produtos.length, "produtos");
        const tabela = document.getElementById('tabela-produtos');
        const tbody = tabela.querySelector('tbody');
        
        // Limpar tabela
        tbody.innerHTML = '';
        
        // Adicionar produtos à tabela
        produtos.forEach(produto => {
            const tr = document.createElement('tr');
            
            // Célula para código
            const tdCodigo = document.createElement('td');
            tdCodigo.textContent = produto.codigo;
            tr.appendChild(tdCodigo);
            
            // Célula para nome
            const tdNome = document.createElement('td');
            tdNome.textContent = produto.nome;
            tr.appendChild(tdNome);
            
            // Célula para quantidade
            const tdQuantidade = document.createElement('td');
            tdQuantidade.textContent = formatarNumero(produto.quantidade);
            tdQuantidade.className = 'text-end';
            tr.appendChild(tdQuantidade);
            
            // Célula para valor
            const tdValor = document.createElement('td');
            tdValor.textContent = formatarMoeda(produto.valor_total);
            tdValor.className = 'text-end';
            tr.appendChild(tdValor);
            
            tbody.appendChild(tr);
        });
        
        // Se não houver produtos, mostrar mensagem
        if (produtos.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 4;
            td.className = 'text-center';
            td.textContent = 'Nenhum produto encontrado no período selecionado.';
            tr.appendChild(td);
            tbody.appendChild(tr);
        }
    }
    
    // Atualiza o gráfico de vendas
    function atualizarGraficoVendas(dados) {
        const vendasPorDia = dados.vendas_por_dia;
        const datas = Object.keys(vendasPorDia).sort();
        const quantidades = datas.map(data => vendasPorDia[data].quantidade);
        const valores = datas.map(data => vendasPorDia[data].valor);
        
        const ctx = document.getElementById('chart-vendas').getContext('2d');
        
        if (chartVendas) {
            chartVendas.data.labels = datas;
            chartVendas.data.datasets[0].data = quantidades;
            chartVendas.data.datasets[1].data = valores;
            chartVendas.update();
        } else {
            const tipoOperacao = dados.tipo_operacao === 'saida' ? 'Vendas' : 'Compras';
            chartVendas = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: datas,
                    datasets: [
                        {
                            label: `Quantidade de ${tipoOperacao}`,
                            data: quantidades,
                            backgroundColor: 'rgba(52, 152, 219, 0.2)',
                            borderColor: 'rgba(52, 152, 219, 1)',
                            borderWidth: 2,
                            tension: 0.3,
                            yAxisID: 'y-quantidade'
                        },
                        {
                            label: 'Valor Total (R$)',
                            data: valores,
                            backgroundColor: 'rgba(46, 204, 113, 0.2)',
                            borderColor: 'rgba(46, 204, 113, 1)',
                            borderWidth: 2,
                            tension: 0.3,
                            yAxisID: 'y-valor'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        'y-quantidade': {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Quantidade'
                            }
                        },
                        'y-valor': {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Valor (R$)'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Atualiza o gráfico de vendas por NCM
    function atualizarGraficoNCM(dados) {
        // Limitar para os 5 NCMs com maior valor
        const topNCMs = dados.slice(0, 5);
        const ncms = topNCMs.map(item => item.ncm);
        const valores = topNCMs.map(item => item.valor_total);
        
        const ctx = document.getElementById('chart-ncm').getContext('2d');
        
        if (chartNCM) {
            chartNCM.data.labels = ncms;
            chartNCM.data.datasets[0].data = valores;
            chartNCM.update();
        } else {
            chartNCM = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ncms,
                    datasets: [{
                        data: valores,
                        backgroundColor: [
                            'rgba(52, 152, 219, 0.8)',
                            'rgba(46, 204, 113, 0.8)',
                            'rgba(155, 89, 182, 0.8)',
                            'rgba(241, 196, 15, 0.8)',
                            'rgba(231, 76, 60, 0.8)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    label += formatarMoeda(context.raw);
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Atualiza o gráfico mensal
    function atualizarGraficoMensal(dados) {
        const meses = dados.map(item => item.mes);
        const valores = dados.map(item => item.valor_total);
        const quantidades = dados.map(item => item.quantidade);
        
        const ctx = document.getElementById('chart-mensal').getContext('2d');
        
        if (chartMensal) {
            chartMensal.data.labels = meses;
            chartMensal.data.datasets[0].data = valores;
            chartMensal.data.datasets[1].data = quantidades;
            chartMensal.update();
        } else {
            chartMensal = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: meses,
                    datasets: [
                        {
                            label: 'Valor Total (R$)',
                            data: valores,
                            backgroundColor: 'rgba(52, 152, 219, 0.8)',
                            borderColor: 'rgba(52, 152, 219, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-valor'
                        },
                        {
                            label: 'Quantidade de Notas',
                            data: quantidades,
                            type: 'line',
                            backgroundColor: 'rgba(231, 76, 60, 0.2)',
                            borderColor: 'rgba(231, 76, 60, 1)',
                            borderWidth: 2,
                            tension: 0.3,
                            yAxisID: 'y-quantidade'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        'y-valor': {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Valor (R$)'
                            }
                        },
                        'y-quantidade': {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Quantidade'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Exibe mensagem de erro
    function exibirMensagemErro(mensagem) {
        console.error(mensagem);
        alert(mensagem);
    }
    
    // ----- Event Listeners -----
    
    // Alternar entre períodos
    document.querySelectorAll('.periodo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.periodo-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            periodoAtual = this.dataset.periodo;
            carregarDadosDashboard();
        });
    });
    
    // Botão de atualizar
    const btnAtualizar = document.getElementById('btnAtualizar');
    if (btnAtualizar) {
        btnAtualizar.addEventListener('click', carregarDadosDashboard);
    }
    
    // ----- Inicialização -----
    console.log("Inicializando dashboard...");
    carregarDadosDashboard();
    
    // Atualizar dados a cada 5 minutos
    setInterval(carregarDadosDashboard, 5 * 60 * 1000);
}); 