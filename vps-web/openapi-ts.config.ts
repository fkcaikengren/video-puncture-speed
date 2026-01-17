import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://127.0.0.1:8800/openapi.json',
  output: './app/APIs',
  plugins: [{
      name: '@hey-api/client-fetch',
      runtimeConfigPath: '@/hey-api',  // 控制client.gen.ts生成 
    },
  ], 
});