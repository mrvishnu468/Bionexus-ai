const API_BASE_URL = "http://127.0.0.1:8000";

export async function searchDatasets(
  query: string,
  retmax: number = 10,
) {
  const response = await fetch(`${API_BASE_URL}/api/datasets/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      retmax,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to search datasets.");
  }

  return response.json();
}