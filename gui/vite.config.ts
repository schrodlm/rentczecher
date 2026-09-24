import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	// dev.py grants CORS for exactly this origin, a silent port shift would
	// surface as opaque browser errors two layers from the cause.
	server: { port: 5173, strictPort: true }
});
