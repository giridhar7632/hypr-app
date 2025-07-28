import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from './useWebsocket';
import { useCallback, useMemo } from 'react';
import { fetchData } from '@/lib/utils';
import { getLiveQuotes } from '@/app/actions';

export interface Stock {
    ticker: string;
    price: string;
    change_amount: string;
    change_percentage: string;
  }
  
  export interface WebSocketMessage {
    type: string;
    data: Stock[];
  }

export const usePopularQuotes = (isdemo: boolean) => {
  const queryClient = useQueryClient();
  console.log('rendering usePopularQuotes', isdemo)

  // initial data fetch
  const query = useQuery({
    queryKey: ['popular-stocks'],
    queryFn: async (): Promise<Stock[]> => !isdemo ? fetchData(`${process.env.NEXT_PUBLIC_BACKEND_URL || ''}/popular`): await getLiveQuotes(),
  });

  // update query data on websocket message
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'quotes' && message.data) {      
      queryClient.setQueryData<Stock[]>(['popular-stocks'], message.data);
    }
  }, [queryClient]);

  const { sendMessage, isConnected } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || '',
    onMessage: handleWebSocketMessage,
    shouldConnect: !isdemo &&!query.isLoading && !query.isError,
  });

  return useMemo(() => ({
    ...query,
    isWebSocketConnected: isConnected,
    sendWebSocketMessage: sendMessage,
  }), [query, isConnected, sendMessage]);
};