# Dashboard de Vendas e Produtos

Aplicação web para visualização de vendas e produtos vendidos por período, desenvolvida com Python/Flask e JavaScript.

## Recursos

- Dashboard interativo com indicadores de desempenho
- Gráficos de evolução de vendas
- Análise de produtos mais vendidos
- Visualização por NCM (Nomenclatura Comum do Mercosul)
- Resumo mensal de vendas
- Filtros por diferentes períodos (semana, mês, trimestre, ano)

## Requisitos

- Python 3.8+
- PostgreSQL (configurado com dados do Odoo)
- Navegador web moderno

## Instalação

1. Clone o repositório:
   ```
   git clone [URL_DO_REPOSITORIO]
   cd app_vendas
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure a conexão com o banco de dados:
   Edite o arquivo `app.py` e atualize as configurações do banco de dados no dicionário `DB_CONFIG`:
   ```python
   DB_CONFIG = {
       'dbname': 'odoo18',
       'user': 'odoo18',
       'password': 'odoo18',
       'host': 'localhost',
       'port': 5435
   }
   ```

## Uso

1. Inicie a aplicação:
   ```
   python app.py
   ```

2. Acesse a aplicação pelo navegador:
   ```
   http://localhost:8000
   ```

## Estrutura do Projeto

```
app_vendas/
├── app.py              # Aplicação principal (Flask)
├── requirements.txt    # Dependências do projeto
├── static/             # Arquivos estáticos
│   ├── css/            # Estilos CSS
│   ├── js/             # Scripts JavaScript
│   └── images/         # Imagens
└── templates/          # Templates HTML
```

## API Endpoints

A aplicação disponibiliza os seguintes endpoints para acesso via API:

- `/api/vendas/dashboard` - Dados do dashboard de vendas
- `/api/produtos/mais-vendidos` - Lista de produtos mais vendidos
- `/api/vendas/por-periodo` - Vendas agrupadas por período (mês/ano)
- `/api/produtos/por-categoria` - Produtos agrupados por NCM

## Modelo de Dados

A aplicação utiliza o seguinte modelo de dados do Odoo:

- `importar_nfe_nfe` - Notas fiscais
- `importar_nfe_item` - Itens das notas fiscais
- `importar_nfe_produto` - Produtos
- `importar_nfe_emitente` - Emitentes
- `importar_nfe_destinatario` - Destinatários

## Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request 