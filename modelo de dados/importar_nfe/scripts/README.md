# Densificação Semântica de Produtos

Este diretório contém scripts para a densificação semântica dos produtos no módulo Importar NFe.

## Visão Geral

A densificação semântica permite enriquecer os produtos com:

1. **Embeddings vetoriais**: Representações numéricas do produto que capturam seu significado semântico
2. **Descrições enriquecidas**: Descrições técnicas geradas por IA com base nas informações do produto
3. **NCM semântico**: Código NCM sugerido ou corrigido com base em análise semântica

## Requisitos

- Python 3.8+
- Biblioteca OpenAI
- Chave de API da OpenAI
- Acesso ao banco de dados do Odoo

## Configuração

1. Crie um arquivo `.env` na raiz do módulo com a seguinte variável:
   ```
   OPENAI_API_KEY=sua_chave_api_aqui
   ```

2. Instale as dependências necessárias:
   ```bash
   pip install openai python-dotenv requests
   ```

## Uso

### Através da Interface do Odoo

1. **Para um único produto**:
   - Abra o formulário do produto
   - Clique no botão "Gerar Informações Semânticas"

2. **Para múltiplos produtos**:
   - Na visualização em lista, selecione os produtos desejados
   - Clique em "Ação" > "Gerar Informações Semânticas"

3. **Para produtos pendentes**:
   - Acesse o menu "Produtos" > "Processar Produtos Pendentes"

### Através de Scripts

Para processar produtos em lote fora da interface do Odoo:

```bash
cd /caminho/para/odoo
python -m custom-addons.importar_nfe.scripts.generate_embeddings --limit 100
```

Opções disponíveis:
- `--limit N`: Limita o processamento a N produtos
- `--force`: Força o reprocessamento mesmo para produtos que já possuem embeddings

## Campos Adicionados

- `semantic_ncm`: NCM sugerido pela análise semântica
- `ncm_vector`: Embeddings vetoriais do produto (armazenados como binário)
- `semantic_descr`: Descrição enriquecida gerada por IA
- `last_semantic_update`: Data da última atualização semântica

## Arquitetura

- `semantic_processor.py`: Modelo abstrato que fornece métodos para processamento semântico
- `generate_embeddings.py`: Script para processamento em lote via linha de comando
- Métodos no modelo `importar_nfe.produto` para processamento via interface

## Notas

- O processamento consome tokens da API da OpenAI, o que pode gerar custos
- O processamento em lote inclui pausas para evitar limites de taxa da API
- Os embeddings são gerados usando o modelo `text-embedding-3-small`
- As descrições semânticas são geradas usando o modelo `gpt-4o-mini`
