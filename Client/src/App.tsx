import { useEffect, useState } from 'react'
import './App.css'

type Health = {
  "status": string
}

function App() {
  const [data, setData] = useState<Health | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      const reponse = await fetch("/api/health");
      const newData = await reponse.json();
      setData(newData);
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
