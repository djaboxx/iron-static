import commonjs from "@rollup/plugin-commonjs";
import nodeResolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

/** @type {import('rollup').RollupOptions} */
export default {
  input: "src/plugin.ts",
  output: {
    file: "com.iron-static.bridge.sdPlugin/bin/plugin.js",
    format: "cjs",
    sourcemap: false,
  },
  plugins: [
    typescript({
      tsconfig: "./tsconfig.json",
    }),
    nodeResolve({
      browser: false,
      preferBuiltins: true,
    }),
    commonjs(),
  ],
  external: ["child_process", "http", "net", "os", "path", "fs"],
};
