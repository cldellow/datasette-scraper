import resolve from '@rollup/plugin-node-resolve';
import commonjs from 'rollup-plugin-commonjs';
import json from '@rollup/plugin-json';
import { terser } from 'rollup-plugin-terser';

export default {
  input: 'editor.js',
  output: {
    file: 'editor.bundle.js',
    format: 'iife'
  },
  plugins: [
    json(),
    resolve(),
    commonjs({
      include: 'node_modules/**',
      namedExports: {
        'node_modules/react-is/index.js': ['Memo', 'isFragment', 'ForwardRef'],
        'node_modules/react/index.js': ['useLayoutEffect', 'createContext', 'useContext', 'forwardRef', 'createElement', 'Fragment', 'useRef', 'Children', 'cloneElement', 'isValidElement', 'useState', 'useMemo', 'useCallback', 'useEffect', 'Component', 'useReducer', 'useDebugValue', 'useImperativeHandle', 'memo', 'createRef'],
        'node_modules/react/jsx-runtime.js': ['jsx', 'jsxs'],
        'node_modules/react-dom/index.js': ['flushSync', 'createPortal'],
      }
    }),
    process.env.NODE_ENV === 'production' && terser({
      compress: {
        keep_infinity: true,
        pure_getters: true,
        passes: 10,
      },
      ecma: 2016,
      toplevel: false,
      format: {
      },
    }),
  ]
};
