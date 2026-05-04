import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface AsyncDataOptions<T> {
  enabled?: boolean;
  refetchInterval?: false | number | ((data: T | undefined) => false | number);
}

interface AsyncDataState<T> {
  data: T | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<T | undefined>;
}

export function useAsyncData<T>(
  loader: () => Promise<T>,
  dependencies: readonly unknown[],
  options: AsyncDataOptions<T> = {}
): AsyncDataState<T> {
  const { enabled = true, refetchInterval = false } = options;
  const [data, setData] = useState<T>();
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const requestId = useRef(0);
  const dataRef = useRef<T>();

  const refetch = useCallback(async () => {
    if (!enabled) return undefined;

    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;
    setIsLoading(true);
    setError(null);

    try {
      const result = await loader();
      if (requestId.current === currentRequest) {
        dataRef.current = result;
        setData(result);
      }
      return result;
    } catch (err) {
      if (requestId.current === currentRequest) {
        setError(err instanceof Error ? err : new Error('Request failed'));
      }
      return undefined;
    } finally {
      if (requestId.current === currentRequest) {
        setIsLoading(false);
      }
    }
  }, [enabled, loader]);

  useEffect(() => {
    dataRef.current = undefined;
    setData(undefined);
    setError(null);
    setIsLoading(enabled);
    void refetch();
  }, dependencies);

  useEffect(() => {
    if (!enabled) return;

    const interval =
      typeof refetchInterval === 'function'
        ? refetchInterval(dataRef.current)
        : refetchInterval;

    if (!interval) return;

    const id = window.setInterval(() => {
      void refetch();
    }, interval);

    return () => window.clearInterval(id);
  }, [enabled, refetch, refetchInterval, data]);

  return useMemo(
    () => ({ data, isLoading, error, refetch }),
    [data, isLoading, error, refetch]
  );
}

export function useMutation<TArgs extends unknown[], TResult>(
  mutation: (...args: TArgs) => Promise<TResult>,
  onSettled?: () => void
) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (...args: TArgs) => {
      setIsPending(true);
      setError(null);
      try {
        return await mutation(...args);
      } catch (err) {
        const normalizedError = err instanceof Error ? err : new Error('Request failed');
        setError(normalizedError);
        throw normalizedError;
      } finally {
        setIsPending(false);
        onSettled?.();
      }
    },
    [mutation, onSettled]
  );

  const mutate = useCallback(
    (...args: TArgs) => {
      void mutateAsync(...args);
    },
    [mutateAsync]
  );

  return { mutate, mutateAsync, isPending, error };
}
