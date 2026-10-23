module.exports = [
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true }
      },
      globals: {
        React: "readonly",
        TEAMS: "readonly",
        TENANTKEY: "readonly",
        Route: "readonly",
        console: "readonly",
        alert: "readonly",
        confirm: "readonly",
        Promise: "readonly",
        AbortController: "readonly",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        JSON: "readonly",
        Object: "readonly",
        Array: "readonly",
        Date: "readonly",
        String: "readonly",
        parseInt: "readonly",
        encodeURIComponent: "readonly",
        Error: "readonly",
        URLSearchParams: "readonly",
        Map: "readonly",
        document: "readonly",
        window: "readonly",
        FormData: "readonly",
        Event: "readonly",
      }
    },
    rules: {
      "no-undef": "error",
      "no-unused-vars": "warn",
      "no-redeclare": "error",
      "no-dupe-keys": "error",
      "no-const-assign": "error",
      "no-empty": "warn",
    }
  }
];
