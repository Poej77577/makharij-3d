import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';

export default defineConfig({
 build:{rollupOptions:{input:{
  home:fileURLToPath(new URL('./index.html',import.meta.url)),
  legacy:fileURLToPath(new URL('./legacy.html',import.meta.url)),
  anatomy:fileURLToPath(new URL('./anatomy.html',import.meta.url)),
  mouth:fileURLToPath(new URL('./mouth.html',import.meta.url)),
 }}},
});
