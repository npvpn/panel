import react from "@vitejs/plugin-react";
import { defineConfig, splitVendorChunkPlugin } from "vite";
import svgr from "vite-plugin-svgr";
import { visualizer } from "rollup-plugin-visualizer";
import tsconfigPaths from "vite-tsconfig-paths";

const i18nVersion = process.env.VITE_BUILD_ID || Date.now().toString();

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    __I18N_VERSION__: JSON.stringify(i18nVersion),
  },
  plugins: [
    tsconfigPaths(),
    react({
      include: "**/*.tsx",
    }),
    svgr(),
    visualizer(),
    splitVendorChunkPlugin(),
  ],
});
