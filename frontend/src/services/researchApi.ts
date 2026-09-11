const API_BASE_URL = "http://127.0.0.1:8000";

export async function startResearch(question: string) {
  const response = await fetch(`${API_BASE_URL}/api/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to start research.");
  }

  return response.json();
}