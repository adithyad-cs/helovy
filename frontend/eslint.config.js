import { defineConfig, globalIgnores } from 'eslint/config'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

const noBrowserStorage = 'Never keep tokens or session data in browser storage (docs/15 §8).'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [tseslint.configs.recommended, reactHooks.configs.flat.recommended],
    rules: {
      // docs/15 §8 frontend hard constraints, enforced by the linter.
      'no-restricted-globals': [
        'error',
        { name: 'localStorage', message: noBrowserStorage },
        { name: 'sessionStorage', message: noBrowserStorage },
      ],
      'no-restricted-properties': [
        'error',
        { object: 'window', property: 'localStorage', message: noBrowserStorage },
        { object: 'window', property: 'sessionStorage', message: noBrowserStorage },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: 'dangerouslySetInnerHTML is forbidden (docs/15 §8, docs/12 §6).',
        },
      ],
    },
  },
])
