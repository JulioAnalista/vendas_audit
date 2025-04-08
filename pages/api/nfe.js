import { Client } from 'pg';

export default async function handler(req, res) {
  // Conexão com o banco de dados utilizando os parâmetros fornecidos
  // db_host = localhost, db_port = 5435, db_user = odoo18, db_password = odoo18
  // Assumindo que o nome do banco de dados é também "odoo18"
  const connectionString = 'postgres://odoo18:odoo18@localhost:5435/odoo18';
  const client = new Client({ connectionString });

  try {
    await client.connect();

    // Buscar dados de itens, produtos, destinatarios e emitentes de NFe
    const [itensResult, produtosResult, destinatariosResult, emitentesResult] = await Promise.all([
      client.query('SELECT * FROM itens'),
      client.query('SELECT * FROM produtos'),
      client.query('SELECT * FROM destinatarios'),
      client.query('SELECT * FROM emitentes')
    ]);

    await client.end();

    res.status(200).json({
      itens: itensResult.rows,
      produtos: produtosResult.rows,
      destinatarios: destinatariosResult.rows,
      emitentes: emitentesResult.rows
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
