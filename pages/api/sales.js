import { Client } from 'pg';

export default async function handler(req, res) {
  const client = new Client({
    connectionString: process.env.DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/salesdb'
  });

  try {
    await client.connect();

    // Consulta de exemplo para agrupar vendas por data
    const result = await client.query(`
      SELECT DATE(created_at) as date, SUM(amount) as amount
      FROM sales
      GROUP BY DATE(created_at)
      ORDER BY DATE(created_at)
    `);
    
    await client.end();
    res.status(200).json({ sales: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
