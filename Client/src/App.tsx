import { useEffect, useState } from 'react'
import './App.css'
import { getHealth, type Health } from './api';

function App() {
  const [data, setData] = useState<Health | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      const health = await getHealth();
      setData(health);
    };
  
    fetchData()
  }, [])
  
  if (data) {
    console.log(data);
    return <div className='App'>{data.status}</div>
  }
  else {
    return null;
}
}

export default App
