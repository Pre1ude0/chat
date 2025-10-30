import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        host: "0.0.0.0",
        proxy: {
            "/api": {
                target: "http://backend:8000", // Backend server
                changeOrigin: true, // Ensure the request appears to come from the frontend server
                rewrite: (path) => path.replace(/^\/api/, ""), // It removes the /api from the request address, so it will truly be used only for differentiation
            },
            "/ws": {
                target: "ws://backend:8000", // Backend WebSocket server
                ws: true, // Enable WebSocket proxying
                changeOrigin: true,
            },
        },
    },
});
