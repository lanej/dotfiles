import js from '@eslint/js';
import comments from '@eslint-community/eslint-plugin-eslint-comments';
import tseslint from 'typescript-eslint';

// The runner supplies the SAME strict Programs used by the compiler. A project
// service reading the original permissive tsconfig would undermine the overlay.
export default function config(root, programs) {
  return tseslint.config({
    files: ['**/*.{ts,tsx,mts,cts}'],
    extends: [js.configs.recommended, ...tseslint.configs.strictTypeChecked],
    languageOptions: {
      parserOptions: { programs, tsconfigRootDir: root },
    },
    plugins: { 'eslint-comments': comments },
    linterOptions: { reportUnusedDisableDirectives: 'error' },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-argument': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unsafe-return': 'error',
      '@typescript-eslint/no-unsafe-type-assertion': 'error',
      '@typescript-eslint/no-floating-promises': [
        'error', { ignoreVoid: false, checkThenables: true },
      ],
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/return-await': ['error', 'error-handling-correctness-only'],
      '@typescript-eslint/only-throw-error': [
        'error', { allowThrowingAny: false, allowThrowingUnknown: false },
      ],
      '@typescript-eslint/use-unknown-in-catch-callback-variable': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': [
        'error', {
          considerDefaultExhaustiveForUnions: false,
          requireDefaultForNonUnion: true,
        },
      ],
      '@typescript-eslint/no-unnecessary-condition': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-unnecessary-type-parameters': 'error',
      '@typescript-eslint/strict-boolean-expressions': [
        'error', {
          allowString: false, allowNumber: false, allowNullableObject: false,
          allowNullableBoolean: false, allowNullableString: false,
          allowNullableNumber: false, allowNullableEnum: false, allowAny: false,
        },
      ],
      '@typescript-eslint/consistent-type-assertions': [
        'error', { assertionStyle: 'as', objectLiteralTypeAssertions: 'never' },
      ],
      '@typescript-eslint/ban-ts-comment': [
        'error', {
          'ts-ignore': true, 'ts-nocheck': true,
          'ts-expect-error': 'allow-with-description', minimumDescriptionLength: 10,
        },
      ],
      'eslint-comments/require-description': 'error',
      'eslint-comments/no-unlimited-disable': 'error',
      'no-constant-condition': ['error', { checkLoops: false }],
      'no-debugger': 'error',
    },
  });
}
