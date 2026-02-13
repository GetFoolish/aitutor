/// <reference types="vite/client" />

interface ImportMetaEnv {
  // add other env variables here
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'country-list' {
  export function getData(): Array<{ code: string; name: string }>;
  export function getNames(): string[];
  export function getCodes(): string[];
  export function getName(code: string): string | undefined;
  export function getCode(name: string): string | undefined;
}