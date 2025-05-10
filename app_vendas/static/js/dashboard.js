// Dashboard de Vendas - JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // ----- Variáveis Globais -----
    let chartVendas = null;
    let chartNCM = null;
    let chartMensal = null;
    
    // Período atual selecionado
    let filtroTipo = 'semana';
    let filtroAno = new Date().getFullYear();
    let filtroMes = new Date().getMonth() + 1;
    let filtroTrimestre = Math.floor((new Date().getMonth() / 3) + 1);
    let filtroSemana = new Date().toISOString().slice(0, 10);
    let filtroDias = 7; // Padrão para últimos 7 dias
    
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
    
    // ----- Funções de Gerenciamento de Filtros -----
    
    // Inicializar os seletores de período
    function inicializarSeletoresPeriodo() {
        // Preencher o seletor de anos (últimos 5 anos)
        const anoAtual = new Date().getFullYear();
        const seletorAno = document.getElementById('ano-select');
        seletorAno.innerHTML = '';
        
        for (let i = 0; i < 5; i++) {
            const ano = anoAtual - i;
            const option = document.createElement('option');
            option.value = ano;
            option.textContent = ano;
            seletorAno.appendChild(option);
        }
        
        // Configurar estado inicial dos seletores
        document.getElementById('mes-select').value = filtroMes;
        document.getElementById('trimestre-select').value = filtroTrimestre;
        document.getElementById('semana-input').value = filtroSemana;
        
        // Mostrar seletores apropriados para o tipo de filtro atual
        atualizarVisibilidadeSeletores();
    }
    
    // Atualiza quais seletores estão visíveis baseado no tipo de filtro
    function atualizarVisibilidadeSeletores() {
        const seletores = document.querySelectorAll('.periodo-seletor');
        seletores.forEach(seletor => seletor.style.display = 'none');
        
        document.getElementById('seletor-ano').style.display = 'block';
        
        if (filtroTipo === 'mes') {
            document.getElementById('seletor-mes').style.display = 'block';
        } 
        else if (filtroTipo === 'trimestre') {
            document.getElementById('seletor-trimestre').style.display = 'block';
        }
        else if (filtroTipo === 'semana') {
            document.getElementById('seletor-semana').style.display = 'block';
        }
    }
    
    // Constrói os parâmetros de filtro para as requisições
    function construirParametrosFiltro() {
        let params = new URLSearchParams();
        
        params.append('tipo_filtro', filtroTipo);
        
        switch (filtroTipo) {
            case 'ano':
                params.append('ano', filtroAno);
                break;
            case 'trimestre':
                params.append('ano', filtroAno);
                params.append('trimestre', filtroTrimestre);
                break;
            case 'mes':
                params.append('ano', filtroAno);
                params.append('mes', filtroMes);
                break;
            case 'semana':
                params.append('data', filtroSemana);
                break;
            case 'ultimos_dias':
                params.append('dias', filtroDias);
                break;
        }
        
        return params.toString();
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
            
            // Construir parâmetros de filtro
            const params = construirParametrosFiltro();
            console.log(`Parâmetros de filtro: ${params}`);
            
            // Buscar novos dados
            console.log(`Solicitando dados do dashboard...`);
            const resposta = await fetch(`/api/vendas/dashboard?${params}`);
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
            const respostaProdutos = await fetch(`/api/produtos/mais-vendidos?${params}&limite=10`);
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
            const respostaNCM = await fetch(`/api/produtos/por-categoria?${params}`);
            if (!respostaNCM.ok) {
                console.error(`Erro HTTP (NCM): ${respostaNCM.status} ${respostaNCM.statusText}`);
                throw new Error('Falha ao carregar dados por NCM');
            }
            
            const dadosNCM = await respostaNCM.json();
            console.log("Dados de NCM recebidos:", dadosNCM);
            atualizarGraficoNCM(dadosNCM.produtos);
            
            // Buscar dados mensais para o ano selecionado
            console.log("Solicitando dados mensais...");
            const respostaMensal = await fetch(`/api/vendas/por-periodo?ano=${filtroAno}`);
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
        
        // Verificar se há dados para mostrar
        if (datas.length === 0) {
            // Se não houver dados, mostrar mensagem no gráfico
            if (chartVendas) {
                chartVendas.destroy();
                chartVendas = null;
            }
            
            const canvas = document.getElementById('chart-vendas');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillStyle = '#e74c3c';
            ctx.fillText('Nenhum dado disponível para o período selecionado.', canvas.width / 2, canvas.height / 2);
            
            // Também mostrar alerta na página
            const alertaDiv = document.createElement('div');
            alertaDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
            alertaDiv.setAttribute('role', 'alert');
            alertaDiv.innerHTML = `
                <strong>Nenhum dado encontrado!</strong> Não existem dados para o período de ${dados.periodo}.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            // Adicionar alerta antes do gráfico
            const chartContainer = document.querySelector('.chart-container');
            if (chartContainer && !document.querySelector('.alert-warning')) {
                chartContainer.parentNode.insertBefore(alertaDiv, chartContainer);
            }
            
            return;
        } else {
            // Remover alerta se existir
            const alerta = document.querySelector('.alert-warning');
            if (alerta) {
                alerta.remove();
            }
        }
        
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
        
        // Verificar se há dados para mostrar
        if (meses.length === 0) {
            // Se não houver dados, mostrar mensagem no gráfico
            if (chartMensal) {
                chartMensal.destroy();
                chartMensal = null;
            }
            
            const canvas = document.getElementById('chart-mensal');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillStyle = '#e74c3c';
            ctx.fillText('Nenhum dado disponível para o ano selecionado.', canvas.width / 2, canvas.height / 2);
            
            return;
        }
        
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
    
    // Alternar entre tipos de período
    document.querySelectorAll('.periodo-tipo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.periodo-tipo-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            filtroTipo = this.dataset.tipo;
            atualizarVisibilidadeSeletores();
        });
    });
    
    // Botões de período rápido
    document.querySelectorAll('.periodo-rapido-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.periodo-rapido-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            filtroTipo = 'ultimos_dias';
            filtroDias = parseInt(this.dataset.periodo);
            
            // Esconder todos os seletores pois estamos usando período rápido
            const seletores = document.querySelectorAll('.periodo-seletor');
            seletores.forEach(seletor => seletor.style.display = 'none');
            
            // Carregar dados automaticamente
            carregarDadosDashboard();
        });
    });
    
    // Mudança no seletor de ano
    document.getElementById('ano-select').addEventListener('change', function() {
        filtroAno = parseInt(this.value);
    });
    
    // Mudança no seletor de mês
    document.getElementById('mes-select').addEventListener('change', function() {
        filtroMes = parseInt(this.value);
    });
    
    // Mudança no seletor de trimestre
    document.getElementById('trimestre-select').addEventListener('change', function() {
        filtroTrimestre = parseInt(this.value);
    });
    
    // Mudança no seletor de semana
    document.getElementById('semana-input').addEventListener('change', function() {
        filtroSemana = this.value;
    });
    
    // Botão de aplicar filtro
    document.getElementById('btnAplicarFiltro').addEventListener('click', function() {
        carregarDadosDashboard();
    });
    
    // Botão de atualizar
    const btnAtualizar = document.getElementById('btnAtualizar');
    if (btnAtualizar) {
        btnAtualizar.addEventListener('click', carregarDadosDashboard);
    }
    
    // ----- Inicialização -----
    console.log("Inicializando dashboard...");
    inicializarSeletoresPeriodo();
    carregarDadosDashboard();
    
    // Atualizar dados a cada 5 minutos
    setInterval(carregarDadosDashboard, 5 * 60 * 1000);
    
    // ----- Dashboard de Produtos -----
    
    // Variáveis para o dashboard de produtos
    let tabelaProdutos = null;
    let produtosData = [];
    let paginaAtual = 1;
    let tamanhoPagina = 10;
    let totalPaginas = 0;
    
    // Função para abrir o modal de produtos
    function abrirModalProdutos() {
        // Limpar tabela de produtos existente
        document.getElementById('produtos-table-body').innerHTML = '';
        
        // Resetar paginação
        paginaAtual = 1;
        
        // Carregar produtos
        carregarProdutos();
        
        // Abrir modal
        const modalProdutos = new bootstrap.Modal(document.getElementById('modalProdutos'));
        modalProdutos.show();
    }
    
    // Função para carregar produtos
    async function carregarProdutos(pagina = 1, limite = 10, filtro = '') {
        try {
            // Mostrar loader
            document.getElementById('produtos-loader').style.display = 'block';
            document.getElementById('produtos-table-body').innerHTML = '';
            
            // Construir parâmetros
            const params = new URLSearchParams();
            params.append('pagina', pagina);
            params.append('limite', limite);
            
            if (filtro) {
                params.append('filtro', filtro);
            }
            
            // Fazer requisição
            const resposta = await fetch(`/api/produtos/listar?${params.toString()}`);
            
            if (!resposta.ok) {
                throw new Error(`Erro HTTP: ${resposta.status}`);
            }
            
            const dados = await resposta.json();
            produtosData = dados.produtos;
            totalPaginas = Math.ceil(dados.total / limite);
            
            // Atualizar informações de paginação
            document.getElementById('produtos-pagina-atual').textContent = pagina;
            document.getElementById('produtos-total-paginas').textContent = totalPaginas;
            
            // Preencher tabela
            preencherTabelaProdutos(produtosData);
            
            // Esconder loader
            document.getElementById('produtos-loader').style.display = 'none';
            
            // Habilitar/desabilitar botões de paginação
            document.getElementById('btn-anterior').disabled = pagina <= 1;
            document.getElementById('btn-proximo').disabled = pagina >= totalPaginas;
            
        } catch (erro) {
            console.error('Erro ao carregar produtos:', erro);
            document.getElementById('produtos-loader').style.display = 'none';
            document.getElementById('produtos-table-body').innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger">
                        Erro ao carregar produtos: ${erro.message}
                    </td>
                </tr>
            `;
        }
    }
    
    // Função para preencher a tabela de produtos
    function preencherTabelaProdutos(produtos) {
        const tbody = document.getElementById('produtos-table-body');
        tbody.innerHTML = '';
        
        if (produtos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        Nenhum produto encontrado.
                    </td>
                </tr>
            `;
            return;
        }
        
        produtos.forEach(produto => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => mostrarDetalhesProduto(produto));
            
            // Código do produto
            const tdCodigo = document.createElement('td');
            tdCodigo.textContent = produto.codigo || '-';
            tr.appendChild(tdCodigo);
            
            // EAN (código de barras)
            const tdEan = document.createElement('td');
            tdEan.textContent = produto.ean || '-';
            tr.appendChild(tdEan);
            
            // Nome do produto
            const tdNome = document.createElement('td');
            tdNome.textContent = produto.nome;
            tr.appendChild(tdNome);
            
            // NCM
            const tdNcm = document.createElement('td');
            tdNcm.textContent = produto.ncm || '-';
            tr.appendChild(tdNcm);
            
            // Preço
            const tdPreco = document.createElement('td');
            tdPreco.textContent = formatarMoeda(produto.preco_medio || 0);
            tdPreco.className = 'text-end';
            tr.appendChild(tdPreco);
            
            tbody.appendChild(tr);
        });
    }
    
    // Função para mostrar detalhes do produto
    function mostrarDetalhesProduto(produto) {
        // Fechar modal de produtos
        const modalProdutos = bootstrap.Modal.getInstance(document.getElementById('modalProdutos'));
        modalProdutos.hide();
        
        // Preencher modal de detalhes
        document.getElementById('produto-detalhe-titulo').textContent = produto.nome;
        document.getElementById('produto-detalhe-codigo').textContent = produto.codigo || '-';
        document.getElementById('produto-detalhe-ean').textContent = produto.ean || '-';
        document.getElementById('produto-detalhe-ncm').textContent = produto.ncm || '-';
        document.getElementById('produto-detalhe-descricao').textContent = produto.descricao || 'Sem descrição disponível';
        document.getElementById('produto-detalhe-preco').textContent = formatarMoeda(produto.preco_medio || 0);
        document.getElementById('produto-detalhe-unidade').textContent = produto.unidade || '-';
        
        // Mostrar histórico de preços se disponível
        const historicoPrecos = document.getElementById('produto-historico-precos');
        historicoPrecos.innerHTML = '';
        
        if (produto.historico_precos && produto.historico_precos.length > 0) {
            produto.historico_precos.forEach(item => {
                const tr = document.createElement('tr');
                
                const tdData = document.createElement('td');
                tdData.textContent = item.data;
                tr.appendChild(tdData);
                
                const tdPreco = document.createElement('td');
                tdPreco.textContent = formatarMoeda(item.preco);
                tdPreco.className = 'text-end';
                tr.appendChild(tdPreco);
                
                historicoPrecos.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 2;
            td.className = 'text-center';
            td.textContent = 'Nenhum histórico disponível';
            tr.appendChild(td);
            historicoPrecos.appendChild(tr);
        }
        
        // Abrir modal de detalhes
        const modalDetalhes = new bootstrap.Modal(document.getElementById('modalProdutoDetalhes'));
        modalDetalhes.show();
    }
    
    // Função para buscar produtos
    function buscarProdutos() {
        const filtro = document.getElementById('produtos-busca').value.trim();
        paginaAtual = 1; // Resetar para primeira página
        carregarProdutos(paginaAtual, tamanhoPagina, filtro);
    }
    
    // ----- Event Listeners para Dashboard de Produtos -----
    
    // Botão para abrir modal de produtos
    document.getElementById('btnVerProdutos').addEventListener('click', abrirModalProdutos);
    
    // Botões de paginação
    document.getElementById('btn-anterior').addEventListener('click', () => {
        if (paginaAtual > 1) {
            paginaAtual--;
            const filtro = document.getElementById('produtos-busca').value.trim();
            carregarProdutos(paginaAtual, tamanhoPagina, filtro);
        }
    });
    
    document.getElementById('btn-proximo').addEventListener('click', () => {
        if (paginaAtual < totalPaginas) {
            paginaAtual++;
            const filtro = document.getElementById('produtos-busca').value.trim();
            carregarProdutos(paginaAtual, tamanhoPagina, filtro);
        }
    });
    
    // Campo de busca
    document.getElementById('produtos-busca').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscarProdutos();
        }
    });
    
    // Botão de busca
    document.getElementById('btn-buscar-produtos').addEventListener('click', buscarProdutos);
}); 