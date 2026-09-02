// Sensor de TypeScript do motor. Mora FORA do repo alvo.
//
// Roda como: eslint --no-config-lookup -c <este arquivo> --max-warnings 0 <arquivo>
// O `--no-config-lookup` ignora a configuração do projeto, e o flat config resolve
// os `import` de plugin relativo A ESTE ARQUIVO — é o que permite o node_modules
// viver aqui e nenhuma linha entrar no repositório de trabalho.
//
// Escopo deliberado: só o que é TRAPAÇA, nunca estilo.
//   - o ESLint e o Prettier do próprio projeto continuam mandando no estilo;
//   - regra de fronteira entre módulos (eslint-plugin-boundaries) precisa da
//     estrutura real de um repo e entra num arquivo por repo, quando houver repo
//     Angular liberado para teste.
//
// Sem regra que exija tipo (`parserOptions.project`) de propósito: exigiria o
// caminho absoluto do tsconfig do alvo e um programa TypeScript carregado, o que
// custa segundos por edição. O servidor de linguagem já entrega o erro de tipo.

import tseslint from 'typescript-eslint';
import noOnlyTests from 'eslint-plugin-no-only-tests';
import jasmine from 'eslint-plugin-jasmine';

export default [
  {
    files: ['**/*.{ts,tsx,mts,cts}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      'no-only-tests': noOnlyTests,
      jasmine,
    },
    rules: {
      // teste que não roda, ou que roda sozinho e esconde os outros
      'no-only-tests/no-only-tests': ['error', { block: ['describe', 'it', 'test', 'fdescribe', 'fit'], focus: ['only'] }],
      'jasmine/no-disabled-tests': 'error',
      'jasmine/no-focused-tests': 'error',

      // buraco engolindo erro
      'no-empty': ['error', { allowEmptyCatch: false }],

      // fuga do sistema de tipos
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/ban-ts-comment': ['error', { 'ts-ignore': true, 'ts-nocheck': true, 'ts-expect-error': 'allow-with-description' }],

      // sobra que finge implementação
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-debugger': 'error',
      'no-alert': 'error',
    },
  },
  {
    // JavaScript solto: mesmas regras que não dependem do parser de TS
    files: ['**/*.{js,mjs,cjs}'],
    plugins: { 'no-only-tests': noOnlyTests, jasmine },
    rules: {
      'no-only-tests/no-only-tests': 'error',
      'jasmine/no-disabled-tests': 'error',
      'no-empty': ['error', { allowEmptyCatch: false }],
      'no-debugger': 'error',
    },
  },
];
