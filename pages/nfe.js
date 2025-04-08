import { useEffect, useState } from 'react';

export default function NFE() {
  const [data, setData] = useState({
    itens: [],
    produtos: [],
    destinatarios: [],
    emitentes: []
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/nfe')
      .then((res) => res.json())
      .then((data) => setData(data))
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div style={{ padding: '20px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
      <h1 style={{ textAlign: 'center', color: '#333' }}>Dashboard NFE</h1>
      
      <section style={{ marginBottom: '40px' }}>
        <h2>Itens</h2>
        <pre>{JSON.stringify(data.itens, null, 2)}</pre>
      </section>
      
      <section style={{ marginBottom: '40px' }}>
        <h2>Produtos</h2>
        <pre>{JSON.stringify(data.produtos, null, 2)}</pre>
      </section>
      
      <section style={{ marginBottom: '40px' }}>
        <h2>Destinatários</h2>
        <pre>{JSON.stringify(data.destinatarios, null, 2)}</pre>
      </section>
      
      <section style={{ marginBottom: '40px' }}>
        <h2>Emitentes</h2>
        <pre>{JSON.stringify(data.emitentes, null, 2)}</pre>
      </section>
    </div>
  );
}
