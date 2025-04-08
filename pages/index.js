import { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function Dashboard() {
  const [salesData, setSalesData] = useState([]);

  useEffect(() => {
    fetch('/api/sales')
      .then((res) => res.json())
      .then((data) => setSalesData(data.sales || []))
      .catch((err) => console.error(err));
  }, []);

  const chartData = {
    labels: salesData.map(item => item.date),
    datasets: [
      {
        label: "Vendas",
        data: salesData.map(item => Number(item.amount)),
        fill: false,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
      },
    ],
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
      <h1 style={{ textAlign: 'center', color: '#333' }}>Dashboard de Vendas</h1>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <Line data={chartData} />
      </div>
    </div>
  );
}
