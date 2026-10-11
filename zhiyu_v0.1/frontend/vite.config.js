import {defineConfig} from 'vite';
export default defineConfig({server:{host:'127.0.0.1',port:8772,strictPort:true,proxy:{'/v1':'http://127.0.0.1:8000'}},preview:{host:'127.0.0.1',port:8772,strictPort:true},build:{sourcemap:false}});
