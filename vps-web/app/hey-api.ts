import type { CreateClientConfig } from '@/APIs/client.gen';

export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  // responseStyle: 'data', // 不开启，默认会多包一层data字段
});