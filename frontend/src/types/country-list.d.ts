declare module 'country-list' {
  interface CountryData {
    code: string;
    name: string;
  }
  
  export function getData(): CountryData[];
  export function getName(code: string): string | undefined;
  export function getCode(name: string): string | undefined;
  export function getNameList(): Record<string, string>;
  export function getCodeList(): Record<string, string>;
}
