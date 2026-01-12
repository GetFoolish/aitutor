/**
 * Global configuration for @khanacademy/math-input
 * This file provides the i18n strings that the math-input library expects
 */

// Import the mock strings from Perseus
import { mockStrings } from './package/perseus/src/strings';

// Declare global type for window
declare global {
    interface Window {
        // @khanacademy/math-input expects this global object
        KA?: {
            language?: string;
            languageCode?: string;
        };
    }
}

// Initialize global KA object if it doesn't exist
if (typeof window !== 'undefined') {
    window.KA = window.KA || {};
    window.KA.language = 'en';
    window.KA.languageCode = 'en';
}

// Export empty object to make this a module
export { };
