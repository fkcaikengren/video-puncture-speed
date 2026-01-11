import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://127.0.0.1:8800/openapi.json',
  output: './app/APIs',
  plugins: ['@hey-api/client-fetch'], 
});