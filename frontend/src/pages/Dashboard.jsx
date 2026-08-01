import { useLocation } from "react-router-dom";

function Dashboard() {
  const location = useLocation();
  const data = location.state;

  if (!data) {
    return (
      <div className="p-8">
        No report analyzed yet — go back and upload one first.
      </div>
    );
  }

  const { statement, ratios } = data;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Financial Analysis</h1>

      <h2 className="text-lg font-semibold mb-2">Extracted Data</h2>
      <table className="mb-6 border-collapse">
        <tbody>
          {Object.entries(statement).map(([key, value]) => (
            <tr key={key} className="border-b">
              <td className="pr-4 py-1 font-medium">{key}</td>
              <td className="py-1">{value ?? "N/A"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-lg font-semibold mb-2">Ratios</h2>
      <table className="border-collapse">
        <tbody>
          {Object.entries(ratios).map(([key, value]) => (
            <tr key={key} className="border-b">
              <td className="pr-4 py-1 font-medium">{key}</td>
              <td className="py-1">{value ?? "N/A"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Dashboard;