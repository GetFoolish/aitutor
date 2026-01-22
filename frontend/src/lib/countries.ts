/**
 * Country list utility using country-list library
 */
import { getData } from 'country-list';

export interface Country {
  code: string;
  name: string;
}

/**
 * Get list of all countries as { code, name } objects, sorted alphabetically
 */
export function getCountryList(): Country[] {
  const countries = getData();
  return countries
    .map((country: any) => ({
      code: country.code,
      name: country.name
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Get country name by code
 */
export function getCountryName(code: string): string | undefined {
  const countries = getCountryList();
  return countries.find(c => c.code === code)?.name;
}

/**
 * Get country code by name (case-insensitive, fuzzy match)
 */
export function getCountryCodeByName(name: string): string | undefined {
  if (!name) return undefined;
  
  const countries = getCountryList();
  const normalizedName = name.trim().toLowerCase();
  
  // Exact match first
  let country = countries.find(
    c => c.name.toLowerCase() === normalizedName
  );
  
  // If no exact match, try partial match
  if (!country) {
    country = countries.find(
      c => c.name.toLowerCase().includes(normalizedName) || 
           normalizedName.includes(c.name.toLowerCase())
    );
  }
  
  return country?.code;
}

/**
 * Find country name that best matches the given string (for IP geolocation)
 */
export function findMatchingCountryName(detectedCountry: string): string | null {
  if (!detectedCountry) return null;
  
  const countries = getCountryList();
  const normalized = detectedCountry.trim().toLowerCase();
  
  // Try exact match
  let match = countries.find(c => c.name.toLowerCase() === normalized);
  
  // Try partial match
  if (!match) {
    match = countries.find(
      c => c.name.toLowerCase().includes(normalized) ||
           normalized.includes(c.name.toLowerCase())
    );
  }
  
  return match ? match.name : null;
}

