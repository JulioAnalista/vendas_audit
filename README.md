# Dashboard de Vendas

Este projeto é um dashboard moderno desenvolvido com Next.js e React para análise de dados de vendas armazenadas em um banco de dados PostgreSQL.

## Recursos

- Visualização de vendas por período utilizando gráficos (Chart.js e react-chartjs-2).
- API integrada para consulta de dados de vendas do banco de dados PostgreSQL.
- Dashboard moderno com design responsivo e esquema de cores agradáveis.

## Pré-requisitos

- Node.js (versão LTS recomendada)
- PostgreSQL

## Instalação

1. Clone o repositório:
   ```
   git clone <URL_DO_REPOSITORIO>
   cd dashboard-vendas
   ```

2. Instale as dependências:
   ```
   npm install
   ```

3. Configure o acesso ao banco de dados:
   
   Crie um arquivo `.env` na raiz do projeto com a seguinte variável:
   ```
   DATABASE_URL=postgres://usuario:senha@localhost:5432/salesdb
   ```
   Substitua `usuario`, `senha` e `salesdb` conforme sua configuração do PostgreSQL.

## Como Executar

Para iniciar o servidor de desenvolvimento, use:
```
npm run dev
```

Acesse `http://localhost:3000` em seu navegador para ver o dashboard.

## Estrutura do Projeto

- `pages/index.js`: Página principal do dashboard com o gráfico de vendas.
- `pages/api/sales.js`: API que consulta o banco de dados PostgreSQL e retorna dados de vendas por data.
- `pages/_app.js`: Componente de entrada que importa os estilos globais.
- `styles/globals.css`: Estilos globais do projeto.

## Personalização

- Os dados são buscados através de uma consulta PostgreSQL no endpoint `/api/sales`. A consulta agrupa os dados por data e soma os valores das vendas.
- As cores e o design estão definidos em `styles/globals.css` e no componente de dashboard em `pages/index.js`.
- Sinta-se à vontade para customizar os estilos e a consulta SQL conforme suas necessidades.

## Observação

Certifique-se de que o banco de dados PostgreSQL esteja em execução e que a tabela de vendas exista com, pelo menos, as colunas `created_at` (data de criação) e `amount` (valor da venda).
