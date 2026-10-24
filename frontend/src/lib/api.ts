export type HealthResult = { status: "ok" } | { status: "error" };

export async function checkHealth(
  baseUrl: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
): Promise<HealthResult> {
  try {
    const response = await fetch(`${baseUrl}/health`);
    if (!response.ok) {
      return { status: "error" };
    }
    return { status: "ok" };
  } catch {
    return { status: "error" };
  }
}
