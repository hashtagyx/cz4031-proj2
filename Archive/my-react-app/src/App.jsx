import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);

  const handleQueryChange = (event) => {
    setQuery(event.target.value);
  };

  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default form submission behavior

    try {
      const response = await axios.post('http://localhost:5000/execute-query', { query });
      setResult(response.data);
      console.log(response.data);
    } catch (error) {
      console.error('Error making API call:', error);
      setResult(error.response.data || 'Error occurred');
    }
  };

  return (
    <div className="App">
      <h1>SQL Query Executor</h1>
      <form onSubmit={handleSubmit}>
        <textarea value={query} onChange={handleQueryChange} rows="4" cols="50" />
        <br />
        <button type="submit">Execute Query</button>
      </form>
      <div>
        <h2>Query Result:</h2>
        {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </div>
  );
}

export default App;
