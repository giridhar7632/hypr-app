import { fetchData } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

export const useHealthCheck = () => {
    const query = useQuery({
        queryKey: ['health-check'],
        queryFn: async () => {
            if (!process.env.NEXT_PUBLIC_BACKEND_URL) {
                console.warn("NEXT_PUBLIC_BACKEND_URL is not set. Assuming backend is unavailable.");
                return { success: false, reason: "Backend URL not configured" };
            }

            try {
                const response = await fetchData(`${process.env.NEXT_PUBLIC_BACKEND_URL}/health`);
                return response;
            } catch (error) {
                console.error("Health check failed:", error);
                return { success: false, error: error };
            }
        },
        refetchOnWindowFocus: true,
        refetchOnMount: true,
        refetchInterval: false
    });

    return query;
}
