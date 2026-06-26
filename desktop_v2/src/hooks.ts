import { useQuery, type QueryKey, type UseQueryOptions } from "@tanstack/react-query";

export function useApiQuery<T>(
  queryKey: QueryKey,
  loader: () => Promise<T>,
  options?: Omit<UseQueryOptions<T, Error, T, QueryKey>, "queryKey" | "queryFn">,
) {
  const query = useQuery<T, Error, T, QueryKey>({
    queryKey,
    queryFn: loader,
    ...options,
  });

  return {
    data: query.data ?? null,
    error: query.error,
    loading: query.isLoading,
    fetching: query.isFetching,
    refetch: query.refetch,
  };
}
